import io
import json
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, init_db
from app.models.models import Quiz, QuizQuestion, QuizAttempt
from app.services.quiz_service import quiz_service, QuizGenerationError
from tests.pdf_helpers import generate_test_pdf

client = TestClient(app)


def setup_module(module):
    """Ensure database is initialized."""
    init_db()


def test_clean_json_response_recovery():
    """Verify _clean_json_response recovers from various structured and malformed formats."""
    # 1. Standard array
    arr = [{"question_text": "Q1?", "options": ["A", "B", "C", "D"], "correct_answer": "A"}]
    assert quiz_service._clean_json_response(json.dumps(arr)) == arr

    # 2. Markdown fenced JSON array
    fenced = f"```json\n{json.dumps(arr)}\n```"
    assert quiz_service._clean_json_response(fenced) == arr

    # 3. Top-level object with 'questions' key
    obj = {"questions": arr}
    assert quiz_service._clean_json_response(json.dumps(obj)) == arr

    # 4. Top-level object with 'quiz' key
    quiz_obj = {"quiz": arr}
    assert quiz_service._clean_json_response(json.dumps(quiz_obj)) == arr

    # 5. Preamble text before JSON
    preamble = f"Here is the quiz:\n{json.dumps(obj)}\nGood luck!"
    assert quiz_service._clean_json_response(preamble) == arr

    # 6. Single question dict wrapped
    single_q = {"question_text": "Single Q?", "options": ["1", "2", "3", "4"], "correct_answer": "1"}
    assert quiz_service._clean_json_response(json.dumps(single_q)) == [single_q]


def test_validate_and_normalize_question_resilience():
    """Verify _validate_and_normalize_question normalizes options, letter answers, and explanations."""
    # 1. Letter answer ("B") mapped to options[1]
    raw = {
        "question_text": "What is the capital of France?",
        "options": ["Berlin", "Paris", "Madrid", "Rome"],
        "correct_answer": "B",
        "explanation": "Paris is the capital.",
        "page_reference": 1
    }
    norm = quiz_service._validate_and_normalize_question(raw)
    assert norm["correct_answer"] == "Paris"
    assert len(norm["options"]) == 4

    # 2. Fewer than 4 options padded to 4
    raw_short = {
        "question_text": "True or False?",
        "options": ["True", "False"],
        "correct_answer": "True",
        "explanation": "It is true."
    }
    norm_short = quiz_service._validate_and_normalize_question(raw_short, default_page=2)
    assert len(norm_short["options"]) == 4
    assert len(set(norm_short["options"])) == 4
    assert norm_short["correct_answer"] == "True"
    assert norm_short["page_reference"] == 2

    # 3. Duplicate options made unique
    raw_dup = {
        "question_text": "Which is best?",
        "options": ["Same", "Same", "Other", "Another"],
        "correct_answer": "Same"
    }
    norm_dup = quiz_service._validate_and_normalize_question(raw_dup)
    assert len(norm_dup["options"]) == 4
    assert len(set(norm_dup["options"])) == 4


@pytest.mark.asyncio
async def test_quiz_generation_and_grading_flow():
    """Verify endpoint generates quiz, hides answers before submission, and grades accurately."""
    pdf = generate_test_pdf([
        "Operating systems manage computer hardware and software resources.",
        "Process scheduling determines which thread receives CPU time."
    ])
    files = {"file": ("os_notes.pdf", io.BytesIO(pdf), "application/pdf")}
    up = client.post("/api/documents/upload", files=files)
    assert up.status_code == 201
    doc_id = up.json()["id"]

    mock_llm_json = {
        "questions": [
            {
                "question_text": "What does an operating system manage?",
                "options": ["Hardware and software", "Only networks", "Only monitors", "Only printers"],
                "correct_answer": "Hardware and software",
                "explanation": "OS manages hardware and software resources.",
                "page_reference": 1
            },
            {
                "question_text": "What does process scheduling determine?",
                "options": ["CPU allocation", "Disk formatting", "Power supply", "Keyboard mapping"],
                "correct_answer": "CPU allocation",
                "explanation": "Scheduling allocates CPU time to processes.",
                "page_reference": 2
            },
            {
                "question_text": "Which component manages memory?",
                "options": ["Kernel memory manager", "BIOS", "Audio card", "Ethernet port"],
                "correct_answer": "Kernel memory manager",
                "explanation": "Memory manager handles RAM allocation.",
                "page_reference": 1
            }
        ]
    }
    dummy_req = httpx.Request("POST", "http://localhost:11434/api/generate")
    mock_resp = httpx.Response(200, json={"response": json.dumps(mock_llm_json)}, request=dummy_req)

    try:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            gen_res = client.post(
                "/api/quizzes/generate",
                json={
                    "document_ids": [doc_id],
                    "title": "OS Fundamentals Quiz",
                    "difficulty": "Medium",
                    "num_questions": 3
                }
            )
            assert gen_res.status_code == 201
            quiz_data = gen_res.json()
            quiz_id = quiz_data["id"]
            assert quiz_data["total_questions"] == 3

            # Privacy rule: ensure answers and explanations are hidden
            for q in quiz_data["questions"]:
                assert "correct_answer" not in q
                assert "explanation" not in q
                assert len(q["options"]) == 4

            # Submit answers (2 correct, 1 wrong)
            q1, q2, q3 = quiz_data["questions"]
            sub_res = client.post(
                f"/api/quizzes/{quiz_id}/submit",
                json={
                    "answers": {
                        str(q1["id"]): "Hardware and software",
                        str(q2["id"]): "CPU allocation",
                        str(q3["id"]): "Wrong Answer"
                    }
                }
            )
            assert sub_res.status_code == 200
            grade = sub_res.json()
            assert grade["score"] == 2
            assert grade["total_questions"] == 3
            assert grade["percentage"] == 66.7
            assert len(grade["results"]) == 3
            # Check citations & explanations revealed upon submission
            for r in grade["results"]:
                assert r["explanation"] is not None
                assert r["page_reference"] in [1, 2]

    finally:
        client.delete(f"/api/documents/{doc_id}")


def test_malformed_json_recovery_variations():
    """Verify JSON extractor handles conversational preambles, nested arrays, and skips invalid items."""
    # Embedded JSON inside conversational response with extra whitespace
    raw = """
    Certainly! Here are your quiz questions:
    ```json
    {
      "questions": [
        {
          "question_text": "What is Python?",
          "options": ["A snake", "A programming language", "A coffee", "A car"],
          "correct_answer": "A programming language",
          "explanation": "Python is a high-level language.",
          "page_reference": 3
        }
      ]
    }
    ```
    Hope this helps you study!
    """
    cleaned = quiz_service._clean_json_response(raw)
    assert len(cleaned) == 1
    assert cleaned[0]["question_text"] == "What is Python?"

    # Empty question text raises ValueError in normalization
    with pytest.raises(ValueError, match="Question text cannot be empty"):
        quiz_service._validate_and_normalize_question({"question_text": "", "options": ["A", "B", "C", "D"], "correct_answer": "A"})


def test_grading_scoring_and_case_insensitivity():
    """Verify grading logic handles case insensitivity, whitespace, and perfect/zero scores."""
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        # Create a test quiz directly in SQLite
        quiz = Quiz(title="Test Math Quiz", difficulty="Easy", total_questions=2)
        db.add(quiz)
        db.commit()
        db.refresh(quiz)

        q1 = QuizQuestion(
            quiz_id=quiz.id,
            question_text="2 + 2 = ?",
            correct_answer="4",
            explanation="Basic addition.",
            page_reference=1
        )
        q1.options = ["1", "2", "3", "4"]

        q2 = QuizQuestion(
            quiz_id=quiz.id,
            question_text="Capital of Japan?",
            correct_answer="Tokyo",
            explanation="Tokyo is the capital.",
            page_reference=2
        )
        q2.options = ["Tokyo", "Kyoto", "Osaka", "Nagoya"]

        db.add_all([q1, q2])
        db.commit()

        # Submit: q1 correct with leading whitespace, q2 correct with different casing ("tokyo")
        graded = quiz_service.submit_and_grade_quiz(
            db=db,
            quiz_id=quiz.id,
            answers={str(q1.id): "  4  ", str(q2.id): "tokyo"}
        )
        assert graded["score"] == 2
        assert graded["percentage"] == 100.0

        # Submit: both wrong
        graded_zero = quiz_service.submit_and_grade_quiz(
            db=db,
            quiz_id=quiz.id,
            answers={str(q1.id): "1", str(q2.id): "Osaka"}
        )
        assert graded_zero["score"] == 0
        assert graded_zero["percentage"] == 0.0

        # Verify attempt records were persisted
        attempts = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz.id).all()
        assert len(attempts) == 2

    finally:
        # Cleanup
        db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz.id).delete()
        db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).delete()
        db.query(Quiz).filter(Quiz.id == quiz.id).delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_fatal_ollama_error_fails_fast_without_retrying():
    """Verify that OllamaConnectionException immediately fails without performing multiple retry attempts."""
    from app.services.ollama_service import OllamaConnectionException, ollama_service
    from app.database.session import SessionLocal

    db = SessionLocal()
    call_count = 0

    async def mock_fail_fast(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise OllamaConnectionException("Server connection refused")

    with patch.object(ollama_service, "generate", side_effect=mock_fail_fast):
        with pytest.raises(OllamaConnectionException):
            await quiz_service.generate_quiz(
                db=db,
                document_ids=[1],
                num_questions=3
            )
        # Should fail on attempt 1 without redundant retries
        assert call_count == 1
    db.close()

