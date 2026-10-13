import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.progress import StudyProgressResponse
from app.services.progress_service import progress_service

logger = logging.getLogger("ai_study_buddy.api.progress")

router = APIRouter()


@router.get(
    "/summary",
    response_model=StudyProgressResponse,
    summary="Get learning progress and study metrics",
    description="Aggregates completed quizzes, average score percentages, cards due, and performance history."
)
def get_study_progress(db: Session = Depends(get_db)) -> StudyProgressResponse:
    """Returns analytics and study summary data for the dashboard."""
    data = progress_service.get_progress_summary(db)
    return StudyProgressResponse(**data)
