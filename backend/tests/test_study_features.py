import io
import json
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal, init_db
from app.models.models import Document, DocumentChunk, Quiz, QuizQuestion, QuizAttempt, Flashcard
from tests.pdf_helpers import generate_test_pdf

client = TestClient(app)


def setup_module(module):
    """Initialize database tables before tests."""
    init_db()


def test_empty_progress_dashboard():
    """Verify progress summary returns 0s without division-by-zero errors when database is empty."""
    response = client.get("/api/progress/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_quizzes" in data
    assert "total_attempts" in data
    assert "average_quiz_score" in data
    assert data["average_quiz_score"] >= 0.0
    assert "total_flashcards" in data
    assert "cards_due_for_review" in data
    assert isinstance(data["recent_attempts"], list)
    assert isinstance(data["performance_history"], list)


@pytest.mark.asyncio
async def test_quiz_generation_privacy_and_grading():
    """Test full quiz lifecycle: generate, verify privacy (no leakage), submit, grade, and record attempt."""
    # 1. Upload a document
    pdf = generate_test_pdf([
        "The cell membrane is a phospholipid bilayer that regulates the transport of materials entering and exiting the cell.",
        "Active transport requires ATP energy to pump molecules against their concentration gradient."
    ])
    files = {"file": ("biology_cells.pdf", io.BytesIO(pdf), "application/pdf")}
    up_res = client.post("/api/documents/upload", files=files)
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    mock_quiz_json = [
        {
            "question_text": "What is the primary structure of the cell membrane?",
            "options": ["Phospholipid bilayer", "Cellulose wall", "Protein sheath", "Lipid monolayer"],
            "correct_answer": "Phospholipid bilayer",
            "explanation": "The membrane consists of a bilayer of phospholipids.",
            "page_reference": 1
        },
        {
            "question_text": "Which process requires ATP energy to transport molecules?",
            "options": ["Passive diffusion", "Active transport", "Osmosis", "Facilitated diffusion"],
            "correct_answer": "Active transport",
            "explanation": "Active transport uses cellular ATP.",
            "page_reference": 2
        }
    ]
    dummy_req = httpx.Request("POST", "http://localhost:11434/api/generate")
    mock_resp = httpx.Response(200, json={"response": json.dumps(mock_quiz_json)}, request=dummy_req)

    try:
        # 2. Generate Quiz
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            gen_res = client.post(
                "/api/quizzes/generate",
                json={
                    "document_ids": [doc_id],
                    "title": "Cell Biology Mastery Quiz",
                    "difficulty": "Medium",
                    "num_questions": 2
                }
            )
            assert gen_res.status_code == 201
            quiz_data = gen_res.json()
            quiz_id = quiz_data["id"]
            assert quiz_data["title"] == "Cell Biology Mastery Quiz"
            assert len(quiz_data["questions"]) == 2

            # 3. CRITICAL PRIVACY CHECK: ensure correct_answer & explanation are NOT leaked before submission
            for q in quiz_data["questions"]:
                assert "correct_answer" not in q
                assert "explanation" not in q
                assert len(q["options"]) == 4

            # 4. Check GET /api/quizzes/{id} also hides answers
            get_res = client.get(f"/api/quizzes/{quiz_id}")
            assert get_res.status_code == 200
            for q in get_res.json()["questions"]:
                assert "correct_answer" not in q
                assert "explanation" not in q

            # 5. Submit Quiz (1 correct, 1 wrong)
            q1 = quiz_data["questions"][0]
            q2 = quiz_data["questions"][1]
            sub_res = client.post(
                f"/api/quizzes/{quiz_id}/submit",
                json={
                    "answers": {
                        str(q1["id"]): "Phospholipid bilayer",  # Correct
                        str(q2["id"]): "Passive diffusion"       # Wrong
                    }
                }
            )
            assert sub_res.status_code == 200
            grade = sub_res.json()
            assert grade["score"] == 1
            assert grade["total_questions"] == 2
            assert grade["percentage"] == 50.0

            # 6. Verify correct answers and explanations are now returned after submission
            r1 = [r for r in grade["results"] if r["question_id"] == q1["id"]][0]
            r2 = [r for r in grade["results"] if r["question_id"] == q2["id"]][0]
            assert r1["is_correct"] is True
            assert r1["correct_answer"] == "Phospholipid bilayer"
            assert r2["is_correct"] is False
            assert r2["correct_answer"] == "Active transport"

            # 7. Check Attempt is persisted in SQLite
            att_res = client.get(f"/api/quizzes/{quiz_id}/attempts")
            assert att_res.status_code == 200
            attempts = att_res.json()
            assert len(attempts) >= 1
            assert attempts[0]["score"] == 1
            assert attempts[0]["percentage"] == 50.0

    finally:
        client.delete(f"/api/documents/{doc_id}")


@pytest.mark.asyncio
async def test_quiz_generation_malformed_json_retry():
    """Verify that completely unparseable model response triggers error handling."""
    pdf = generate_test_pdf([
        "Newton's laws of motion describe the relationship between a body and the forces acting upon it in classical mechanics. "
        "The first law states that an object remains at rest or in uniform motion unless acted upon by a force."
    ])
    up_res = client.post("/api/documents/upload", files={"file": ("physics_test.pdf", io.BytesIO(pdf), "application/pdf")})
    doc_id = up_res.json()["id"]

    dummy_req = httpx.Request("POST", "http://localhost:11434/api/generate")
    # Non-json response
    mock_resp = httpx.Response(200, json={"response": "I am unable to output JSON."}, request=dummy_req)

    try:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            res = client.post(
                "/api/quizzes/generate",
                json={"document_ids": [doc_id], "difficulty": "Easy", "num_questions": 3}
            )
            assert res.status_code == 502
    finally:
        client.delete(f"/api/documents/{doc_id}")


def test_quiz_insufficient_content_rejection():
    """Verify rejection when documents have no content or invalid IDs."""
    res = client.post(
        "/api/quizzes/generate",
        json={"document_ids": [999999], "difficulty": "Medium", "num_questions": 5}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_flashcard_generation_and_spaced_repetition():
    """Test flashcard generation, spaced repetition review intervals, and due scheduling."""
    pdf = generate_test_pdf([
        "Photosynthesis converts light energy into chemical energy stored in glucose.",
        "Chlorophyll absorbs blue and red light while reflecting green light."
    ])
    up_res = client.post("/api/documents/upload", files={"file": ("botany.pdf", io.BytesIO(pdf), "application/pdf")})
    doc_id = up_res.json()["id"]

    mock_cards = [
        {
            "question": "What is the primary function of photosynthesis?",
            "answer": "Converts light energy into chemical energy stored in glucose.",
            "page_reference": 1
        },
        {
            "question": "Which light spectrum does chlorophyll reflect?",
            "answer": "Green light.",
            "page_reference": 2
        }
    ]
    dummy_req = httpx.Request("POST", "http://localhost:11434/api/generate")
    mock_resp = httpx.Response(200, json={"response": json.dumps(mock_cards)}, request=dummy_req)

    try:
        # 1. Generate Flashcards
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            fc_res = client.post(
                "/api/flashcards/generate",
                json={"document_ids": [doc_id], "num_cards": 2}
            )
            assert fc_res.status_code == 201
            cards = fc_res.json()["flashcards"]
            assert len(cards) == 2
            card1 = cards[0]
            card2 = cards[1]

            # 2. Check due cards endpoint
            due_res = client.get("/api/flashcards/due")
            assert due_res.status_code == 200
            due_ids = [c["id"] for c in due_res.json()["flashcards"]]
            assert card1["id"] in due_ids

            # 3. Review Card 1 with "Easy" (should schedule ~4 days)
            rev_easy = client.post(
                f"/api/flashcards/{card1['id']}/review",
                json={"rating": "Easy"}
            )
            assert rev_easy.status_code == 200
            easy_data = rev_easy.json()
            assert easy_data["difficulty_rating"] == "Easy"
            assert easy_data["interval_days"] >= 4.0
            assert easy_data["review_count"] == 1

            # 4. Review Card 2 with "Hard" (should schedule 1 day)
            rev_hard = client.post(
                f"/api/flashcards/{card2['id']}/review",
                json={"rating": "Hard"}
            )
            assert rev_hard.status_code == 200
            hard_data = rev_hard.json()
            assert hard_data["difficulty_rating"] == "Hard"
            assert hard_data["interval_days"] == 1.0

            # 5. Delete Flashcard
            del_res = client.delete(f"/api/flashcards/{card1['id']}")
            assert del_res.status_code == 200

    finally:
        client.delete(f"/api/documents/{doc_id}")


def test_progress_summary_with_data():
    """Verify study progress aggregation includes documents, quizzes, attempts, and flashcards."""
    summary_res = client.get("/api/progress/summary")
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert "total_documents" in data
    assert "total_quizzes" in data
    assert "total_attempts" in data
    assert "average_quiz_score" in data
    assert "total_flashcards" in data
    assert "cards_due_for_review" in data


def test_flashcard_json_cleaning_variations():
    """Verify flashcard JSON parsing handles array, wrapped objects, and fences."""
    from app.services.flashcard_service import flashcard_service

    # 1. Plain array
    arr = [{"question": "What is RAM?", "answer": "Random Access Memory", "page_reference": 1}]
    assert flashcard_service._clean_json_response(json.dumps(arr)) == arr

    # 2. Wrapped in 'flashcards' key
    wrapped_fc = {"flashcards": arr}
    assert flashcard_service._clean_json_response(json.dumps(wrapped_fc)) == arr

    # 3. Wrapped in 'cards' key
    wrapped_cards = {"cards": arr}
    assert flashcard_service._clean_json_response(json.dumps(wrapped_cards)) == arr

    # 4. Markdown code fenced
    fenced = f"```json\n{json.dumps(wrapped_fc)}\n```"
    assert flashcard_service._clean_json_response(fenced) == arr

    # 5. Conversational preamble and postscript
    convo = f"Here are your flashcards:\n{json.dumps(wrapped_fc)}\nGood luck studying!"
    assert flashcard_service._clean_json_response(convo) == arr


@pytest.mark.asyncio
async def test_flashcard_single_call_batch_generation():
    """Verify that multiple flashcards are generated in a single Ollama LLM call (never 1 request per card)."""
    from app.services.flashcard_service import flashcard_service
    from app.services.ollama_service import ollama_service

    db = SessionLocal()
    mock_payload = {
        "flashcards": [
            {"question": f"Q{i}", "answer": f"A{i}", "page_reference": i}
            for i in range(1, 6)
        ]
    }
    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return {"response": json.dumps(mock_payload)}

    with patch.object(ollama_service, "generate", side_effect=mock_generate):
        cards = await flashcard_service.generate_flashcards(
            db=db,
            document_ids=[1],
            num_cards=5
        )
        assert len(cards) == 5
        # Must be exactly 1 LLM inference request for all 5 cards
        assert call_count == 1

        # Clean up inserted test cards
        for c in cards:
            db.delete(c)
        db.commit()
    db.close()


@pytest.mark.asyncio
async def test_flashcard_fatal_error_fails_fast_without_retrying():
    """Verify fatal Ollama connection error fails fast without multiple retry attempts."""
    from app.services.flashcard_service import flashcard_service
    from app.services.ollama_service import ollama_service, OllamaConnectionException

    db = SessionLocal()
    call_count = 0

    async def mock_fail_fast(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise OllamaConnectionException("Local server unreachable")

    with patch.object(ollama_service, "generate", side_effect=mock_fail_fast):
        with pytest.raises(OllamaConnectionException):
            await flashcard_service.generate_flashcards(
                db=db,
                document_ids=[1],
                num_cards=5
            )
        assert call_count == 1
    db.close()

