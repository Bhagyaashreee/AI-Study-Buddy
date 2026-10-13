from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class RecentAttemptItem(BaseModel):
    """Summary of a recent quiz attempt."""
    attempt_id: int
    quiz_id: int
    quiz_title: str
    difficulty: str
    score: int
    total_questions: int
    percentage: float
    completed_at: datetime


class PerformanceHistoryItem(BaseModel):
    """Performance point for progress chart visualization."""
    attempt_id: int
    quiz_title: str
    percentage: float
    completed_at: datetime


class StudyProgressResponse(BaseModel):
    """Complete study progress analytics dashboard data."""
    total_documents: int
    total_quizzes: int
    total_attempts: int
    average_quiz_score: float
    total_flashcards: int
    cards_due_for_review: int
    recent_attempts: List[RecentAttemptItem]
    performance_history: List[PerformanceHistoryItem]
