import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.models import Document, Quiz, QuizAttempt, Flashcard

logger = logging.getLogger("ai_study_buddy.progress")


class ProgressService:
    """Service calculating study metrics, quiz performances, and spaced repetition analytics."""

    @staticmethod
    def get_progress_summary(db: Session) -> Dict[str, Any]:
        """Aggregates all persistent student learning data from SQLite."""
        now = datetime.now(timezone.utc)

        # 1. Document metrics
        total_docs = db.query(Document).count()

        # 2. Quiz metrics
        total_quizzes = db.query(Quiz).count()
        total_attempts = db.query(QuizAttempt).count()

        # Average score percentage across all completed attempts (handle empty database safely)
        avg_score_query = db.query(func.avg(QuizAttempt.percentage)).scalar()
        average_quiz_score = round(float(avg_score_query), 1) if avg_score_query is not None else 0.0

        # 3. Flashcard metrics
        total_flashcards = db.query(Flashcard).count()
        
        # Cards due: next_review_at is in past or None
        cards_due = (
            db.query(Flashcard)
            .filter((Flashcard.next_review_at <= now) | (Flashcard.next_review_at.is_(None)))
            .count()
        )

        # 4. Recent quiz attempts (latest 6)
        recent_attempts_raw = (
            db.query(QuizAttempt, Quiz)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .order_by(QuizAttempt.completed_at.desc())
            .limit(6)
            .all()
        )

        recent_attempts: List[Dict[str, Any]] = [
            {
                "attempt_id": att.id,
                "quiz_id": q.id,
                "quiz_title": q.title,
                "difficulty": q.difficulty,
                "score": att.score,
                "total_questions": att.total_questions,
                "percentage": att.percentage,
                "completed_at": att.completed_at
            }
            for att, q in recent_attempts_raw
        ]

        # 5. Performance history over time (chronological order)
        history_raw = (
            db.query(QuizAttempt, Quiz)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .order_by(QuizAttempt.completed_at.asc())
            .limit(20)
            .all()
        )

        performance_history: List[Dict[str, Any]] = [
            {
                "attempt_id": att.id,
                "quiz_title": q.title,
                "percentage": att.percentage,
                "completed_at": att.completed_at
            }
            for att, q in history_raw
        ]

        return {
            "total_documents": total_docs,
            "total_quizzes": total_quizzes,
            "total_attempts": total_attempts,
            "average_quiz_score": average_quiz_score,
            "total_flashcards": total_flashcards,
            "cards_due_for_review": cards_due,
            "recent_attempts": recent_attempts,
            "performance_history": performance_history
        }


progress_service = ProgressService()
