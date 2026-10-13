import json
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import Document, DocumentChunk, Flashcard
from app.services.ollama_service import (
    ollama_service,
    OllamaServiceException,
    OllamaConnectionException,
    OllamaModelNotFoundException,
    OllamaTimeoutException,
)

logger = logging.getLogger("ai_study_buddy.flashcards")


class FlashcardGenerationError(Exception):
    """Raised when flashcard generation fails after retries."""
    pass


class FlashcardService:
    """Service for generating study flashcards and managing spaced repetition reviews."""

    @staticmethod
    def _clean_json_response(raw_text: str) -> List[Dict[str, Any]]:
        """Extracts JSON array or object containing flashcards from model response."""
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        try:
            data = json.loads(text)
        except Exception:
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
            for key in ["flashcards", "cards", "items", "data", "results"]:
                if key in data and isinstance(data[key], list):
                    return [item for item in data[key] if isinstance(item, dict)]
            if "question" in data and "answer" in data:
                return [data]
            raise ValueError("Expected JSON containing flashcards list.")
        elif isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        else:
            raise ValueError("Expected JSON array or object containing flashcards.")

    async def generate_flashcards(
        self,
        db: Session,
        document_ids: List[int],
        num_cards: int = 5
    ) -> List[Flashcard]:
        """Generates multiple study flashcards in a single optimized local Ollama inference call."""
        docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
        if not docs:
            raise ValueError("None of the specified documents exist.")

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        if not chunks:
            raise ValueError("Selected documents contain no text chunks. Please upload more complete notes.")

        # Representative chunk curation across document sections proportional to card count (max 5 chunks)
        max_chunks = min(len(chunks), max(2, min(num_cards, 5)))
        if len(chunks) <= max_chunks:
            selected_chunks = chunks
        else:
            step = len(chunks) / max_chunks
            selected_chunks = [chunks[int(i * step)] for i in range(max_chunks)]

        doc_map = {d.id: d.original_filename for d in docs}
        default_page = selected_chunks[0].page_number if selected_chunks else 1
        excerpts: List[str] = []

        for c in selected_chunks:
            raw_dname = doc_map.get(c.document_id, "Doc")
            dname = raw_dname[:25] + "..." if len(raw_dname) > 28 else raw_dname
            clean_content = " ".join(c.content.split())
            if len(clean_content) > 650:
                clean_content = clean_content[:650] + "..."
            excerpts.append(f"[{dname}, Page {c.page_number or 1}]:\n{clean_content}")

        context = "\n\n".join(excerpts)
        if len(context.strip()) < 50:
            raise ValueError("Insufficient document content to generate flashcards.")

        prompt = (
            f"Based STRICTLY on the following study excerpts, generate EXACTLY {num_cards} high-yield study flashcards.\n\n"
            f"Excerpts:\n"
            f"{context}\n\n"
            f"REQUIREMENTS:\n"
            f"1. Output a JSON object with a 'flashcards' array containing EXACTLY {num_cards} objects.\n"
            f"2. Each flashcard object MUST follow this schema:\n"
            f"   - 'question': Clear, concise concept or term question.\n"
            f"   - 'answer': Factual, direct answer (1-2 sentences, < 30 words).\n"
            f"   - 'page_reference': Integer page number where the information appears in the excerpts.\n\n"
            f"JSON Schema:\n"
            f'{{"flashcards": [{{"question": "Key concept question?", "answer": "Concise definition.", "page_reference": 1}}]}}'
        )

        token_limit = max(260, min(1400, num_cards * 85 + 60))
        target_min = min(2, num_cards) if num_cards <= 3 else min(3, num_cards)
        now = datetime.now(timezone.utc)
        last_error = None
        max_attempts = 2

        for attempt in range(max_attempts):
            try:
                gen_result = await ollama_service.generate(
                    prompt=prompt,
                    system_prompt="You are an expert tutor. Output ONLY a valid JSON object matching the requested schema. Keep answers direct and concise.",
                    temperature=0.2 + (attempt * 0.1),
                    max_tokens=token_limit,
                    format="json"
                )
                raw_json = self._clean_json_response(gen_result["response"])

                created_flashcards: List[Flashcard] = []
                for item in raw_json:
                    q = str(item.get("question", "")).strip()
                    a = str(item.get("answer", "")).strip()
                    if not q or not a:
                        continue

                    raw_page = item.get("page_reference")
                    try:
                        page_ref = int(raw_page) if raw_page is not None else default_page
                    except (ValueError, TypeError):
                        page_ref = default_page

                    # Trim overly verbose answers
                    words = a.split()
                    if len(words) > 40:
                        a = " ".join(words[:40]) + "..."

                    fc = Flashcard(
                        document_id=docs[0].id if docs else None,
                        question=q,
                        answer=a,
                        difficulty_rating="Medium",
                        page_reference=page_ref,
                        review_count=0,
                        last_reviewed_at=None,
                        next_review_at=now
                    )
                    created_flashcards.append(fc)

                if len(created_flashcards) >= target_min:
                    db.add_all(created_flashcards)
                    db.commit()
                    for fc in created_flashcards:
                        db.refresh(fc)
                    return created_flashcards
                else:
                    last_error = ValueError(f"Extracted only {len(created_flashcards)} of {target_min} required flashcards.")
                    logger.warning(f"Flashcard generation attempt {attempt + 1}: {last_error}")

            except (OllamaConnectionException, OllamaModelNotFoundException, OllamaTimeoutException):
                # Fail fast on fatal connection / model errors
                raise
            except (OllamaServiceException, ValueError, json.JSONDecodeError) as exc:
                logger.warning(f"Flashcard generation attempt {attempt + 1} failed: {exc}")
                last_error = exc

        raise FlashcardGenerationError(f"Failed to generate valid flashcards from document notes: {last_error}")

    @staticmethod
    def calculate_next_review(rating: str, current_review_count: int) -> Tuple[datetime, float]:
        """Calculates next spaced repetition review date.
        Schedule logic:
        - Easy:   interval = min(30.0, 4.0 * (1.5 ** current_review_count)) days
        - Medium: interval = min(14.0, 2.0 * (1.2 ** current_review_count)) days
        - Hard:   interval = 1.0 day (reset interval for difficult cards)
        """
        clean_rating = rating.capitalize()
        if clean_rating == "Easy":
            interval = min(30.0, 4.0 * (1.5 ** min(current_review_count, 6)))
        elif clean_rating == "Medium":
            interval = min(14.0, 2.0 * (1.2 ** min(current_review_count, 6)))
        else:  # Hard
            interval = 1.0

        now = datetime.now(timezone.utc)
        next_date = now + timedelta(days=interval)
        return next_date, round(interval, 1)

    def record_review(self, db: Session, flashcard_id: int, rating: str) -> Dict[str, Any]:
        """Records student rating for a card and schedules next review date."""
        card = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if not card:
            raise ValueError(f"Flashcard #{flashcard_id} not found.")

        clean_rating = rating.capitalize()
        if clean_rating not in ["Easy", "Medium", "Hard"]:
            raise ValueError("Rating must be 'Easy', 'Medium', or 'Hard'.")

        now = datetime.now(timezone.utc)
        next_review_date, interval_days = self.calculate_next_review(clean_rating, card.review_count)

        card.difficulty_rating = clean_rating
        card.review_count += 1
        card.last_reviewed_at = now
        card.next_review_at = next_review_date

        db.commit()
        db.refresh(card)

        return {
            "id": card.id,
            "difficulty_rating": card.difficulty_rating,
            "review_count": card.review_count,
            "last_reviewed_at": card.last_reviewed_at,
            "next_review_at": card.next_review_at,
            "interval_days": interval_days,
            "message": f"Card marked '{clean_rating}'. Scheduled for next review in {interval_days} day(s)."
        }


flashcard_service = FlashcardService()
