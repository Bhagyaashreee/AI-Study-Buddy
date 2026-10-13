"""Pydantic request and response schemas."""
from app.schemas.health import HealthResponse, DatabaseHealth, OllamaHealth
from app.schemas.ai import ChatRequest, ChatResponse, OllamaStatusResponse
from app.schemas.documents import (
    DocumentResponse,
    DocumentListResponse,
    DeleteDocumentResponse,
    RAGSourceItem,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.schemas.quiz import (
    QuizGenerateRequest,
    QuizQuestionPublicResponse,
    QuizQuestionFullResponse,
    QuizResponse,
    QuizListItemResponse,
    QuizListResponse,
    QuizSubmitRequest,
    QuestionResultItem,
    QuizSubmitResponse,
    QuizAttemptResponse,
)
from app.schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardListResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
)
from app.schemas.progress import (
    StudyProgressResponse,
    RecentAttemptItem,
    PerformanceHistoryItem,
)

__all__ = [
    "HealthResponse",
    "DatabaseHealth",
    "OllamaHealth",
    "ChatRequest",
    "ChatResponse",
    "OllamaStatusResponse",
    "DocumentResponse",
    "DocumentListResponse",
    "DeleteDocumentResponse",
    "RAGSourceItem",
    "RAGQueryRequest",
    "RAGQueryResponse",
    "QuizGenerateRequest",
    "QuizQuestionPublicResponse",
    "QuizQuestionFullResponse",
    "QuizResponse",
    "QuizListItemResponse",
    "QuizListResponse",
    "QuizSubmitRequest",
    "QuestionResultItem",
    "QuizSubmitResponse",
    "QuizAttemptResponse",
    "FlashcardGenerateRequest",
    "FlashcardResponse",
    "FlashcardListResponse",
    "FlashcardReviewRequest",
    "FlashcardReviewResponse",
    "StudyProgressResponse",
    "RecentAttemptItem",
    "PerformanceHistoryItem",
]
