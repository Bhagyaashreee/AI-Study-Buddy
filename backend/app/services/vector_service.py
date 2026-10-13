import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import Document, DocumentChunk
from app.services.embedding_service import embedding_service

logger = logging.getLogger("ai_study_buddy.vectorstore")


class VectorService:
    """FAISS-CPU vector storage service.
    Maintains vector indexing with explicit chunk ID mappings and local persistence.
    """

    def __init__(self, index_dir: Optional[Path] = None):
        self.index_dir = index_dir or settings.VECTOR_DIR
        self.dimension = settings.EMBEDDING_DIMENSION
        self.index_file = self.index_dir / "faiss_index.bin"
        self.metadata_file = self.index_dir / "vector_metadata.json"
        
        self.index: Optional[faiss.IndexIDMap2] = None
        # Maps str(chunk_id) -> {"chunk_id": int, "document_id": int, "page_number": int, "content": str}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        self._initialize_or_load_index()

    def _initialize_or_load_index(self) -> None:
        """Loads existing index from disk or creates a new IndexIDMap2."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors.")
                return
            except Exception as exc:
                logger.warning(f"Failed to load existing index file: {exc}. Initializing empty index.")

        # Create new Cosine Similarity Index using Inner Product on L2-normalized vectors
        sub_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap2(sub_index)
        self.metadata = {}
        self.save()

    def save(self) -> None:
        """Persists the FAISS index and chunk metadata to disk."""
        if self.index is None:
            return
        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
        logger.debug(f"FAISS index and metadata saved ({self.index.ntotal} vectors).")

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> None:
        """Adds a batch of document chunks and their embeddings into the index.
        Args:
            chunks: List of dicts with {"id": int, "document_id": int, "page_number": int, "content": str}
            embeddings: np.ndarray of shape (len(chunks), dimension), float32
        """
        if len(chunks) == 0:
            return

        if self.index is None:
            self._initialize_or_load_index()

        chunk_ids = np.array([c["id"] for c in chunks], dtype=np.int64)
        
        # Remove any existing vectors with these chunk IDs to avoid duplicates
        try:
            self.index.remove_ids(chunk_ids)
        except Exception:
            pass

        # Ensure embeddings are 2D float32
        vectors = np.asarray(embeddings, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = np.expand_dims(vectors, axis=0)

        # Add to FAISS
        self.index.add_with_ids(vectors, chunk_ids)

        # Store metadata
        for chunk in chunks:
            c_id_str = str(chunk["id"])
            self.metadata[c_id_str] = {
                "chunk_id": chunk["id"],
                "document_id": chunk["document_id"],
                "page_number": chunk.get("page_number", 1),
                "content": chunk["content"]
            }

        self.save()
        logger.info(f"Added {len(chunks)} chunks to FAISS index. Total vectors: {self.index.ntotal}.")

    def delete_document_vectors(self, document_id: int) -> int:
        """Deletes all vectors belonging to a specific document.
        Returns the number of deleted vectors.
        """
        if self.index is None or self.index.ntotal == 0:
            return 0

        # Find all chunk IDs for this document
        to_delete = [
            int(cid) for cid, meta in self.metadata.items()
            if meta.get("document_id") == document_id
        ]

        if not to_delete:
            return 0

        # Remove from FAISS
        ids_array = np.array(to_delete, dtype=np.int64)
        try:
            self.index.remove_ids(ids_array)
        except Exception as exc:
            logger.warning(f"Error removing IDs from FAISS: {exc}")

        # Remove from metadata
        for cid in to_delete:
            self.metadata.pop(str(cid), None)

        self.save()
        logger.info(f"Deleted {len(to_delete)} vectors for document {document_id}. Remaining: {self.index.ntotal}.")
        return len(to_delete)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 4,
        document_ids: Optional[List[int]] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Searches the vector index for chunks most relevant to query_vector.
        Returns a list of dicts with chunk metadata and similarity scores.
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        threshold = similarity_threshold if similarity_threshold is not None else settings.RAG_SIMILARITY_THRESHOLD

        # If document filters are applied, request more raw matches from FAISS to allow filtering
        if document_ids:
            search_k = min(self.index.ntotal, max(top_k * 10, 100))
        else:
            search_k = min(self.index.ntotal, max(top_k * 4, 20))

        q_vec = np.asarray(query_vector, dtype=np.float32)
        if q_vec.ndim == 1:
            q_vec = np.expand_dims(q_vec, axis=0)

        distances, indices = self.index.search(q_vec, search_k)

        results: List[Dict[str, Any]] = []
        raw_distances = distances[0]
        raw_indices = indices[0]

        for score, chunk_id in zip(raw_distances, raw_indices):
            if chunk_id == -1:
                continue

            # Convert numpy float to standard python float
            sim_score = float(score)
            if sim_score < threshold:
                continue

            meta = self.metadata.get(str(chunk_id))
            if not meta:
                continue

            # Check document filter
            if document_ids and meta.get("document_id") not in document_ids:
                continue

            results.append({
                "chunk_id": meta["chunk_id"],
                "document_id": meta["document_id"],
                "page_number": meta.get("page_number", 1),
                "content": meta["content"],
                "similarity_score": round(sim_score, 4)
            })

            if len(results) >= top_k:
                break

        return results

    def rebuild_index_from_db(self, db: Session) -> int:
        """Rebuilds the FAISS index and metadata from all ready Document chunks in SQLite."""
        logger.info("Rebuilding FAISS index from SQLite database...")
        
        # Reset current index
        sub_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap2(sub_index)
        self.metadata = {}

        # Fetch all chunks of ready documents
        chunks = (
            db.query(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.status == "ready")
            .order_by(DocumentChunk.id)
            .all()
        )

        if not chunks:
            self.save()
            logger.info("No chunks found in database. Initialized clean index.")
            return 0

        # Generate embeddings in batch
        texts = [c.content for c in chunks]
        embeddings = embedding_service.embed_texts(texts)

        chunk_data = [
            {
                "id": c.id,
                "document_id": c.document_id,
                "page_number": c.page_number or 1,
                "content": c.content
            }
            for c in chunks
        ]

        self.add_chunks(chunk_data, embeddings)
        logger.info(f"Successfully rebuilt FAISS index with {len(chunks)} chunks.")
        return len(chunks)


vector_service = VectorService()
