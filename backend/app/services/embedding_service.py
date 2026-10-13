import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger("ai_study_buddy.embeddings")


class EmbeddingServiceException(Exception):
    """Base exception for embedding service."""
    pass


class EmbeddingModelNotAvailableError(EmbeddingServiceException):
    """Raised when the local embedding model cannot be loaded."""
    pass


class EmbeddingService:
    """Zero-cost local embedding service powered by sentence-transformers.
    All embeddings run 100% locally on CPU or local GPU.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model: Optional[SentenceTransformer] = None

    def get_model(self) -> SentenceTransformer:
        """Lazily load and cache the SentenceTransformer model singleton."""
        if self._model is None:
            logger.info(f"Loading local embedding model: '{self.model_name}'...")
            try:
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Model '{self.model_name}' loaded successfully. Embedding dimension: {self.dimension}.")
            except Exception as exc:
                logger.error(f"Failed to load sentence-transformers model '{self.model_name}': {exc}")
                raise EmbeddingModelNotAvailableError(
                    f"Local embedding model '{self.model_name}' is unavailable. "
                    "Ensure internet access for initial download or verify local cache."
                ) from exc
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generates L2-normalized embeddings for a list of texts.
        Returns:
            np.ndarray of shape (len(texts), dimension), dtype float32.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        model = self.get_model()
        # normalize_embeddings=True allows using Inner Product (IP) index for Cosine Similarity
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return np.asarray(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Generates a normalized embedding for a single user question.
        Returns:
            np.ndarray of shape (1, dimension), dtype float32.
        """
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query must not be empty.")

        model = self.get_model()
        embedding = model.encode(
            clean_query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        emb_array = np.asarray(embedding, dtype=np.float32)
        if emb_array.ndim == 1:
            emb_array = np.expand_dims(emb_array, axis=0)
        return emb_array


embedding_service = EmbeddingService()
