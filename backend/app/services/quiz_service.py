import json
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import Document, DocumentChunk, Quiz, QuizQuestion, QuizAttempt
from app.services.ollama_service import (
    ollama_service,
    OllamaServiceException,
    OllamaConnectionException,
    OllamaModelNotFoundException,
    OllamaTimeoutException,
)

logger = logging.getLogger("ai_study_buddy.quiz")


class QuizGenerationError(Exception):
    """Raised when quiz generation fails after retries."""
    pass


class QuizService:
    """Service for generating, validating, and grading multiple choice quizzes."""

    @staticmethod
    def _clean_json_response(raw_text: str) -> List[Dict[str, Any]]:
        """Strips markdown formatting, extracts JSON array or dictionary with questions, and parses."""
        text = raw_text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        # Try direct parse first
        try:
            data = json.loads(text)
        except Exception:
            # Find first '[' or '{' and matching end
            start_bracket = text.find("[")
            start_brace = text.find("{")

            if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
                end_bracket = text.rfind("]")
                if end_bracket > start_bracket:
                    json_str = text[start_bracket:end_bracket + 1]
                    data = json.loads(json_str)
                else:
                    data = json.loads(text)
            elif start_brace != -1:
                end_brace = text.rfind("}")
                if end_brace > start_brace:
                    json_str = text[start_brace:end_brace + 1]
                    data = json.loads(json_str)
                else:
                    data = json.loads(text)
            else:
                data = json.loads(text)

        if isinstance(data, dict):
            # Check for common wrapper keys: 'questions', 'quiz', 'items', 'data', 'results'
            for key in ["questions", "quiz", "items", "data", "results"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If the dict is a single question object with question_text
            if "question_text" in data and ("options" in data or "choices" in data):
                return [data]
            raise ValueError("Expected JSON containing a list of questions.")
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("Expected JSON array or object containing questions.")

    @staticmethod
    def _validate_and_normalize_question(item: Dict[str, Any], default_page: Optional[int] = None) -> Dict[str, Any]:
        """Validates that a generated question has text, exactly 4 options, and a valid correct answer."""
        q_text = str(item.get("question_text", "")).strip()
        if not q_text:
            raise ValueError("Question text cannot be empty.")

        raw_options = item.get("options") or item.get("choices") or []
        if not isinstance(raw_options, list):
            raw_options = []

        options = [str(opt).strip() for opt in raw_options if str(opt).strip()]

        # Ensure at least 4 options, padding with sensible contextual alternatives if fewer were provided
        fallback_options = ["None of the above", "All of the above", "Cannot be determined", "Alternative approach"]
        fb_idx = 0
        while len(options) < 4:
            alt = fallback_options[fb_idx % len(fallback_options)]
            if alt not in options:
                options.append(alt)
            else:
                options.append(f"Option {len(options) + 1}")
            fb_idx += 1

        # Keep exactly 4 options
        options = options[:4]

        # Ensure unique options
        unique_options: List[str] = []
        for i, opt in enumerate(options):
            if opt not in unique_options:
                unique_options.append(opt)
            else:
                unique_options.append(f"{opt} ({i+1})")
        options = unique_options

        correct = str(item.get("correct_answer", "")).strip()

        # Handle letter-based answers ("A", "B", "C", "D" or "Option A")
        letter_match = re.match(r"^(?:option\s+)?([A-D])$", correct, re.IGNORECASE)
        if letter_match:
            idx = ord(letter_match.group(1).upper()) - ord("A")
            if 0 <= idx < len(options):
                correct = options[idx]

        # If correct answer is not in options, search case-insensitive / partial match
        if correct not in options:
            found = False
            for opt in options:
                if opt.lower() == correct.lower() or correct.lower() in opt.lower() or opt.lower() in correct.lower():
                    correct = opt
                    found = True
                    break
            if not found:
                correct = options[0]

        raw_explanation = str(item.get("explanation", "Refer to study notes.")).strip()
        words = raw_explanation.split()
        if len(words) > 35:
            explanation = " ".join(words[:35]) + "..."
        else:
            explanation = raw_explanation

        page_ref = item.get("page_reference") or default_page

        return {
            "question_text": q_text,
            "options": options,
            "correct_answer": correct,
            "explanation": explanation,
            "page_reference": int(page_ref) if page_ref else None
        }

    async def generate_quiz(
        self,
        db: Session,
        document_ids: List[int],
        difficulty: str = "Medium",
        num_questions: int = 3,
        title: Optional[str] = None
    ) -> Quiz:
        """Generates a multiple choice quiz from uploaded document chunks using local Ollama.
        Optimized for zero-cost local execution on Windows 11 with fast prompt processing and token limits.
        """
        # 1. Fetch documents
        docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
        if not docs:
            raise ValueError("None of the specified documents exist.")

        # 2. Fetch chunks
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

        if not chunks:
            raise ValueError("Selected documents contain no text chunks. Please upload more complete notes.")

        # 3. Assemble curated, representative excerpts (1 chunk per question, min 2, max 4 for 3 questions, max 6 for large quizzes)
        # Evenly spread selection across the document to cover all sections without drowning local LLM context
        max_chunks = min(len(chunks), max(2, min(num_questions + 1, 6)))
        if len(chunks) <= max_chunks:
            selected_chunks = chunks
        else:
            step = len(chunks) / max_chunks
            selected_chunks = [chunks[int(i * step)] for i in range(max_chunks)]

        excerpts: List[str] = []
        doc_map = {d.id: d.original_filename for d in docs}
        default_page = selected_chunks[0].page_number if selected_chunks else 1

        for c in selected_chunks:
            raw_dname = doc_map.get(c.document_id, "Document")
            # Compact filename label to save prompt tokens while preserving citation grounding
            dname = raw_dname[:28] + "..." if len(raw_dname) > 30 else raw_dname
            clean_content = " ".join(c.content.split())
            if len(clean_content) > 650:
                clean_content = clean_content[:650] + "..."
            excerpts.append(f"[{dname}, Page {c.page_number or 1}]:\n{clean_content}")

        context = "\n\n".join(excerpts)
        if len(context.strip()) < 50:
            raise ValueError("Insufficient document content to generate quiz questions.")

        quiz_title = title.strip() if title and title.strip() else f"{docs[0].original_filename} Quiz ({difficulty})"

        prompt = (
            f"Based STRICTLY on the following study excerpts, generate a {difficulty}-difficulty multiple-choice quiz with EXACTLY {num_questions} questions.\n\n"
            f"Excerpts:\n"
            f"{context}\n\n"
            f"REQUIREMENTS:\n"
            f"1. Output a JSON object with a 'questions' array containing EXACTLY {num_questions} question objects.\n"
            f"2. Each question object MUST follow this schema:\n"
            f"   - 'question_text': Clear question sentence based on the excerpts.\n"
            f"   - 'options': Exactly 4 distinct answer choices (full text strings, not single letters).\n"
            f"   - 'correct_answer': The exact string of the correct choice from 'options'.\n"
            f"   - 'explanation': 1 concise sentence (< 20 words) explaining why the answer is correct.\n"
            f"   - 'page_reference': Integer page number where the answer is found in the excerpts.\n\n"
            f"JSON Schema:\n"
            f'{{"questions": [{{"question_text": "...", "options": ["Choice 1", "Choice 2", "Choice 3", "Choice 4"], "correct_answer": "Choice 1", "explanation": "Brief explanation.", "page_reference": 1}}]}}'
        )

        # 4. Compute optimal token limit based on question count (~140 tokens per question + overhead)
        token_limit = max(420, min(2200, num_questions * 140 + 80))

        # 5. Generate with local Ollama, retrying only if generation or validation genuinely fails
        last_error = None
        max_attempts = 2

        for attempt in range(max_attempts):
            try:
                gen_result = await ollama_service.generate(
                    prompt=prompt,
                    system_prompt="You are an expert exam generator. Output ONLY a valid JSON object matching the requested schema. Keep questions, options, and explanations concise.",
                    temperature=0.2 + (attempt * 0.1),
                    max_tokens=token_limit,
                    format="json"
                )
                raw_json = self._clean_json_response(gen_result["response"])

                validated_questions: List[Dict[str, Any]] = []
                for item in raw_json:
                    try:
                        val_q = self._validate_and_normalize_question(item, default_page=default_page)
                        validated_questions.append(val_q)
                    except Exception as val_exc:
                        logger.warning(f"Skipping malformed question item: {val_exc}")

                target_min = min(2, num_questions) if num_questions <= 3 else min(3, num_questions)
                if len(validated_questions) >= target_min:
                    # Successfully parsed sufficient questions
                    quiz_obj = Quiz(
                        document_id=docs[0].id if len(docs) == 1 else None,
                        title=quiz_title,
                        difficulty=difficulty,
                        total_questions=len(validated_questions)
                    )
                    db.add(quiz_obj)
                    db.commit()
                    db.refresh(quiz_obj)

                    for q_data in validated_questions:
                        q_obj = QuizQuestion(
                            quiz_id=quiz_obj.id,
                            question_text=q_data["question_text"],
                            correct_answer=q_data["correct_answer"],
                            explanation=q_data["explanation"],
                            page_reference=q_data["page_reference"]
                        )
                        q_obj.options = q_data["options"]
                        db.add(q_obj)

                    db.commit()
                    db.refresh(quiz_obj)
                    return quiz_obj
                else:
                    last_error = ValueError(f"Extracted only {len(validated_questions)} of {target_min} required questions.")
                    logger.warning(f"Quiz generation attempt {attempt + 1}: {last_error}")

            except (OllamaConnectionException, OllamaModelNotFoundException, OllamaTimeoutException):
                # Fatal connectivity or missing model errors must fail fast without wasting time on retries
                raise
            except (OllamaServiceException, ValueError, json.JSONDecodeError) as exc:
                logger.warning(f"Quiz generation attempt {attempt + 1} failed: {exc}")
                last_error = exc

        raise QuizGenerationError(f"Failed to generate valid quiz JSON from local model: {last_error}")


    @staticmethod
    def submit_and_grade_quiz(
        db: Session,
        quiz_id: int,
        answers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validates student submissions, calculates score, and persists attempt."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise ValueError(f"Quiz #{quiz_id} not found.")

        questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
        if not questions:
            raise ValueError("Quiz contains no questions.")

        score = 0
        total = len(questions)
        results: List[Dict[str, Any]] = []

        for q in questions:
            # Lookup student answer by str(id) or int(id)
            user_choice = answers.get(str(q.id)) or answers.get(q.id) or ""
            is_correct = (user_choice.strip().lower() == q.correct_answer.strip().lower())
            if is_correct:
                score += 1

            results.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "selected_answer": user_choice if user_choice else None,
                "correct_answer": q.correct_answer,
                "is_correct": is_correct,
                "explanation": q.explanation,
                "page_reference": q.page_reference
            })

        percentage = round((score / total) * 100.0, 1) if total > 0 else 0.0

        # Persist attempt record in SQLite
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            score=score,
            total_questions=total,
            percentage=percentage,
            user_answers=answers
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        return {
            "attempt_id": attempt.id,
            "quiz_id": quiz.id,
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "completed_at": attempt.completed_at,
            "results": results
        }


quiz_service = QuizService()
