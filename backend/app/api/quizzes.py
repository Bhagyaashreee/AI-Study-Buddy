import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Quiz, QuizQuestion, QuizAttempt
from app.schemas.quiz import (
    QuizGenerateRequest,
    QuizResponse,
    QuizQuestionPublicResponse,
    QuizListResponse,
    QuizListItemResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizAttemptResponse,
)
from app.services.quiz_service import quiz_service, QuizGenerationError
from app.services.ollama_service import OllamaServiceException

logger = logging.getLogger("ai_study_buddy.api.quizzes")

router = APIRouter()


@router.post(
    "/generate",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI multiple-choice quiz",
    description="Generates questions from selected uploaded documents using local Ollama."
)
async def generate_quiz(
    request: QuizGenerateRequest,
    db: Session = Depends(get_db)
) -> QuizResponse:
    """Generates a multiple choice quiz from document chunks."""
    try:
        quiz = await quiz_service.generate_quiz(
            db=db,
            document_ids=request.document_ids,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            title=request.title
        )

        public_questions = [
            QuizQuestionPublicResponse(
                id=q.id,
                quiz_id=q.quiz_id,
                question_text=q.question_text,
                options=q.options,
                page_reference=q.page_reference
            )
            for q in quiz.questions
        ]

        return QuizResponse(
            id=quiz.id,
            title=quiz.title,
            difficulty=quiz.difficulty,
            total_questions=quiz.total_questions,
            document_id=quiz.document_id,
            created_at=quiz.created_at,
            questions=public_questions
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except QuizGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except OllamaServiceException as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.error(f"Unexpected error in quiz generation: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the quiz."
        )


@router.get(
    "",
    response_model=QuizListResponse,
    summary="List all quizzes",
    description="Returns metadata and performance summary for all generated quizzes."
)
def list_quizzes(db: Session = Depends(get_db)) -> QuizListResponse:
    """Lists all quizzes with attempt counts and best scores."""
    quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).all()
    items: List[QuizListItemResponse] = []

    for q in quizzes:
        attempts = q.attempts
        best_pct = max([att.percentage for att in attempts]) if attempts else None
        items.append(
            QuizListItemResponse(
                id=q.id,
                title=q.title,
                difficulty=q.difficulty,
                total_questions=q.total_questions,
                document_id=q.document_id,
                created_at=q.created_at,
                attempts_count=len(attempts),
                best_percentage=best_pct
            )
        )

    return QuizListResponse(quizzes=items, total_quizzes=len(items))


@router.get(
    "/{quiz_id}",
    response_model=QuizResponse,
    summary="Get a quiz to take",
    description="Returns quiz questions without exposing correct answers to prevent answer leakage."
)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)) -> QuizResponse:
    """Returns quiz with public questions for taking the test."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz #{quiz_id} not found.")

    public_questions = [
        QuizQuestionPublicResponse(
            id=q.id,
            quiz_id=q.quiz_id,
            question_text=q.question_text,
            options=q.options,
            page_reference=q.page_reference
        )
        for q in quiz.questions
    ]

    return QuizResponse(
        id=quiz.id,
        title=quiz.title,
        difficulty=quiz.difficulty,
        total_questions=quiz.total_questions,
        document_id=quiz.document_id,
        created_at=quiz.created_at,
        questions=public_questions
    )


@router.post(
    "/{quiz_id}/submit",
    response_model=QuizSubmitResponse,
    summary="Submit and grade a quiz",
    description="Grades answers on the backend, saves attempt in SQLite, and reveals explanations."
)
def submit_quiz(
    quiz_id: int,
    request: QuizSubmitRequest,
    db: Session = Depends(get_db)
) -> QuizSubmitResponse:
    """Grades submitted quiz answers and records score."""
    try:
        graded = quiz_service.submit_and_grade_quiz(
            db=db,
            quiz_id=quiz_id,
            answers=request.answers
        )
        return QuizSubmitResponse(**graded)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Error grading quiz #{quiz_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grade quiz submission."
        )


@router.get(
    "/{quiz_id}/attempts",
    response_model=List[QuizAttemptResponse],
    summary="Get past attempts for a quiz",
    description="Returns previous completed attempts and scores for this quiz."
)
def get_quiz_attempts(quiz_id: int, db: Session = Depends(get_db)) -> List[QuizAttemptResponse]:
    """Lists historical attempts for a quiz."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz #{quiz_id} not found.")

    attempts = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).order_by(QuizAttempt.completed_at.desc()).all()
    return [
        QuizAttemptResponse(
            id=att.id,
            quiz_id=att.quiz_id,
            score=att.score,
            total_questions=att.total_questions,
            percentage=att.percentage,
            completed_at=att.completed_at
        )
        for att in attempts
    ]


@router.delete(
    "/{quiz_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a quiz",
    description="Removes a quiz and all associated questions and attempts."
)
def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    """Deletes a quiz and its cascade dependencies."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz #{quiz_id} not found.")
    db.delete(quiz)
    db.commit()
    return {"success": True, "message": f"Quiz #{quiz_id} deleted successfully."}
