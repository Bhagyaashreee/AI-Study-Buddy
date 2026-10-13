import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from app.main import app
from app.core.config import settings
from app.database.session import engine, init_db, check_db_connection, SessionLocal
from app.models.models import Document, DocumentChunk, Quiz, QuizQuestion, QuizAttempt, Flashcard

client = TestClient(app)


def test_database_initialization():
    """Verify that init_db creates all required database tables."""
    init_db()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    
    expected_tables = {
        "documents",
        "document_chunks",
        "quizzes",
        "quiz_questions",
        "quiz_attempts",
        "flashcards"
    }
    for table in expected_tables:
        assert table in table_names, f"Table '{table}' was not created in SQLite database"


def test_database_connectivity():
    """Verify that database connection check returns True."""
    assert check_db_connection() is True


def test_root_endpoint():
    """Verify that root endpoint returns 200 with service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AI Study Buddy"
    assert data["status"] == "online"
    assert "version" in data
    assert "health" in data


def test_health_endpoint():
    """Verify that /api/health returns 200 and accurate system status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "AI Study Buddy"
    assert data["database"]["status"] == "connected"
    assert data["database"]["type"] == "sqlite"
    assert "ollama" in data
    assert "status" in data["ollama"]
    assert data["status"] in ["healthy", "degraded"]


def test_models_persistence():
    """Verify CRUD operations on models in the SQLite database."""
    init_db()
    db = SessionLocal()
    try:
        # 1. Create a test document
        test_doc = Document(
            filename="sample_notes.pdf",
            original_filename="sample_notes.pdf",
            file_path="data/uploads/sample_notes.pdf",
            file_size_bytes=1024,
            page_count=3,
            status="ready"
        )
        db.add(test_doc)
        db.commit()
        db.refresh(test_doc)
        assert test_doc.id is not None

        # 2. Add a document chunk
        chunk = DocumentChunk(
            document_id=test_doc.id,
            chunk_index=0,
            page_number=1,
            content="This is sample study buddy content for testing.",
            char_count=48
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        assert chunk.id is not None
        assert chunk.document_id == test_doc.id

        # 3. Create a quiz with question
        quiz = Quiz(
            document_id=test_doc.id,
            title="Biology Basics Quiz",
            difficulty="Easy",
            total_questions=1
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="What is the powerhouse of the cell?",
            correct_answer="Mitochondria",
            options=["Nucleus", "Mitochondria", "Ribosome", "Endoplasmic Reticulum"],
            explanation="Mitochondria generate ATP."
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        assert question.options == ["Nucleus", "Mitochondria", "Ribosome", "Endoplasmic Reticulum"]

        # 4. Create a quiz attempt
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            score=1,
            total_questions=1,
            percentage=100.0,
            user_answers={str(question.id): "Mitochondria"}
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        assert attempt.user_answers[str(question.id)] == "Mitochondria"

        # 5. Create a flashcard
        flashcard = Flashcard(
            document_id=test_doc.id,
            question="What is ATP?",
            answer="Adenosine Triphosphate, energy currency of the cell.",
            difficulty_rating="Easy",
            page_reference=1
        )
        db.add(flashcard)
        db.commit()
        db.refresh(flashcard)
        assert flashcard.id is not None

        # Cleanup test document and cascades
        db.delete(test_doc)
        db.commit()

        # Verify cascades
        assert db.query(DocumentChunk).filter_by(document_id=test_doc.id).count() == 0
        assert db.query(Quiz).filter_by(id=quiz.id).count() == 0
        assert db.query(Flashcard).filter_by(id=flashcard.id).count() == 0

    finally:
        db.close()
