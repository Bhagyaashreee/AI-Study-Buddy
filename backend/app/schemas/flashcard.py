from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class FlashcardGenerateRequest(BaseModel):
    """Request model for generating flashcards from uploaded notes."""
    document_ids: List[int] = Field(
        ...,
        min_length=1,
        description="One or more document IDs to generate flashcards from."
    )
    num_cards: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of flashcards to generate."
    )


class FlashcardResponse(BaseModel):
    """Flashcard details including spaced repetition metadata."""
    id: int
    document_id: Optional[int] = None
    document_name: Optional[str] = None
    question: str
    answer: str
    difficulty_rating: str
    page_reference: Optional[int] = None
    review_count: int
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    is_due: bool = False
    created_at: datetime


class FlashcardListResponse(BaseModel):
    """List of flashcards."""
    flashcards: List[FlashcardResponse]
    total_cards: int


class FlashcardReviewRequest(BaseModel):
    """Payload to record a spaced repetition review rating."""
    rating: str = Field(
        ...,
        description="Review rating: 'Easy', 'Medium', or 'Hard'."
    )

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        clean = v.capitalize()
        if clean not in ["Easy", "Medium", "Hard"]:
            raise ValueError("Rating must be 'Easy', 'Medium', or 'Hard'.")
        return clean


class FlashcardReviewResponse(BaseModel):
    """Result of recording a flashcard review."""
    id: int
    difficulty_rating: str
    review_count: int
    last_reviewed_at: datetime
    next_review_at: datetime
    interval_days: float
    message: str
