"""API routers export."""
from app.api.ai import router as ai_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.quizzes import router as quizzes_router
from app.api.flashcards import router as flashcards_router
from app.api.progress import router as progress_router

__all__ = [
    "ai_router",
    "documents_router",
    "chat_router",
    "quizzes_router",
    "flashcards_router",
    "progress_router",
]
