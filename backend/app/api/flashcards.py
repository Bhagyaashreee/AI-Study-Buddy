import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Flashcard, Document
from app.schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardListResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
)
from app.services.flashcard_service import flashcard_service, FlashcardGenerationError
from app.services.ollama_service import OllamaServiceException

logger = logging.getLogger("ai_study_buddy.api.flashcards")

router = APIRouter()


def to_flashcard_response(fc: Flashcard, doc_name: Optional[str] = None) -> FlashcardResponse:
    """Helper to convert ORM model to Pydantic FlashcardResponse."""
    now = datetime.now(timezone.utc)
    next_rev = fc.next_review_at
    if next_rev is not None:
        if next_rev.tzinfo is None:
            next_rev = next_rev.replace(tzinfo=timezone.utc)
        is_due = (next_rev <= now)
    else:
        is_due = True

    last_rev = fc.last_reviewed_at
    if last_rev is not None and last_rev.tzinfo is None:
        last_rev = last_rev.replace(tzinfo=timezone.utc)

    created_at = fc.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    name = doc_name or (fc.document.original_filename if fc.document else None)
    return FlashcardResponse(
        id=fc.id,
        document_id=fc.document_id,
        document_name=name,
        question=fc.question,
        answer=fc.answer,
        difficulty_rating=fc.difficulty_rating,
        page_reference=fc.page_reference,
        review_count=fc.review_count,
        last_reviewed_at=last_rev,
        next_review_at=next_rev,
        is_due=is_due,
        created_at=created_at or now
    )


@router.post(
    "/generate",
    response_model=FlashcardListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate flashcards from notes",
    description="Extracts key concepts and generates question-and-answer study flashcards using local Ollama."
)
async def generate_flashcards(
    request: FlashcardGenerateRequest,
    db: Session = Depends(get_db)
) -> FlashcardListResponse:
    """Generates flashcards from selected document chunks."""
    try:
        created = await flashcard_service.generate_flashcards(
            db=db,
            document_ids=request.document_ids,
            num_cards=request.num_cards
        )
        items = [to_flashcard_response(fc) for fc in created]
        return FlashcardListResponse(flashcards=items, total_cards=len(items))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FlashcardGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except OllamaServiceException as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.error(f"Unexpected error generating flashcards: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate flashcards from document notes."
        )


@router.get(
    "",
    response_model=FlashcardListResponse,
    summary="List all flashcards",
    description="Returns all flashcards, optionally filtered by document ID."
)
def list_flashcards(
    document_id: Optional[int] = Query(None, description="Optional document ID filter"),
    db: Session = Depends(get_db)
) -> FlashcardListResponse:
    """Lists flashcards with due status."""
    query = db.query(Flashcard)
    if document_id is not None:
        query = query.filter(Flashcard.document_id == document_id)
    cards = query.order_by(Flashcard.created_at.desc()).all()
    items = [to_flashcard_response(c) for c in cards]
    return FlashcardListResponse(flashcards=items, total_cards=len(items))


@router.get(
    "/due",
    response_model=FlashcardListResponse,
    summary="Get flashcards due for review",
    description="Returns flashcards scheduled for review right now based on spaced repetition."
)
def get_due_flashcards(db: Session = Depends(get_db)) -> FlashcardListResponse:
    """Returns flashcards that are due for review."""
    now = datetime.now(timezone.utc)
    due_cards = (
        db.query(Flashcard)
        .filter((Flashcard.next_review_at <= now) | (Flashcard.next_review_at.is_(None)))
        .order_by(Flashcard.next_review_at.asc())
        .all()
    )
    items = [to_flashcard_response(c) for c in due_cards]
    return FlashcardListResponse(flashcards=items, total_cards=len(items))


@router.post(
    "/{flashcard_id}/review",
    response_model=FlashcardReviewResponse,
    summary="Record spaced repetition review rating",
    description="Marks a card Easy, Medium, or Hard and schedules the next review date."
)
def review_flashcard(
    flashcard_id: int,
    request: FlashcardReviewRequest,
    db: Session = Depends(get_db)
) -> FlashcardReviewResponse:
    """Updates review count, rating, and schedules next review timestamp."""
    try:
        result = flashcard_service.record_review(
            db=db,
            flashcard_id=flashcard_id,
            rating=request.rating
        )
        return FlashcardReviewResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{flashcard_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a flashcard",
    description="Permanently removes a flashcard."
)
def delete_flashcard(flashcard_id: int, db: Session = Depends(get_db)):
    """Deletes a flashcard by ID."""
    card = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Flashcard #{flashcard_id} not found.")
    db.delete(card)
    db.commit()
    return {"success": True, "message": f"Flashcard #{flashcard_id} deleted successfully."}
