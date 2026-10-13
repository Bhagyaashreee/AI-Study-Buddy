"""Business logic and AI services."""
from app.services.ollama_service import (
    OllamaService,
    ollama_service,
    OllamaServiceException,
    OllamaConnectionException,
    OllamaTimeoutException,
    OllamaModelNotFoundException,
    OllamaResponseException,
)
from app.services.pdf_service import (
    PDFService,
    pdf_service,
    PDFProcessingException,
    PDFCorruptedError,
    PDFEmptyError,
    PDFScannedNoOCRError,
)
from app.services.embedding_service import (
    EmbeddingService,
    embedding_service,
    EmbeddingServiceException,
    EmbeddingModelNotAvailableError,
)
from app.services.vector_service import VectorService, vector_service
from app.services.rag_service import RAGService, rag_service
from app.services.quiz_service import QuizService, quiz_service, QuizGenerationError
from app.services.flashcard_service import FlashcardService, flashcard_service
from app.services.progress_service import ProgressService, progress_service

__all__ = [
    "OllamaService",
    "ollama_service",
    "OllamaServiceException",
    "OllamaConnectionException",
    "OllamaTimeoutException",
    "OllamaModelNotFoundException",
    "OllamaResponseException",
    "PDFService",
    "pdf_service",
    "PDFProcessingException",
    "PDFCorruptedError",
    "PDFEmptyError",
    "PDFScannedNoOCRError",
    "EmbeddingService",
    "embedding_service",
    "EmbeddingServiceException",
    "EmbeddingModelNotAvailableError",
    "VectorService",
    "vector_service",
    "RAGService",
    "rag_service",
    "QuizService",
    "quiz_service",
    "QuizGenerationError",
    "FlashcardService",
    "flashcard_service",
    "ProgressService",
    "progress_service",
]
