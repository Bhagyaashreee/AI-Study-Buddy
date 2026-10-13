import logging
import re
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import Document
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.services.ollama_service import ollama_service

logger = logging.getLogger("ai_study_buddy.rag")

# Common student conversational shorthand / slang mapping
SLANG_MAP = {
    r"\bwt\b": "what",
    r"\bwts\b": "what is",
    r"\bimp\b": "important",
    r"\bpls\b": "please",
    r"\bplz\b": "please",
    r"\bb/w\b": "between",
    r"\bdiff\b": "difference",
    r"\bdefn\b": "definition",
    r"\bdef\b": "definition",
    r"\bex\b": "example",
    r"\bu\b": "you",
    r"\bur\b": "your",
    r"\br\b": "are",
}


def normalize_query(text: str) -> str:
    """Normalizes student query by expanding colloquial abbreviations."""
    cleaned = text
    for pattern, replacement in SLANG_MAP.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


class RAGService:
    """Retrieval-Augmented Generation service connecting local FAISS search with Ollama."""

    SYSTEM_PROMPT = (
        "You are AI Study Buddy, a helpful and precise academic tutor. "
        "Your task is to answer the student's question based strictly on the provided study material excerpts. "
        "Guidelines:\n"
        "1. Prioritize information from the provided excerpts.\n"
        "2. When explaining, cite the document name and page reference.\n"
        "3. Never fabricate page numbers, document names, or facts not present in the excerpts.\n"
        "4. If the student asks for a summary, overview, or important/key topics, synthesize the main themes, key concepts, exercises, and topics covered in the provided excerpts.\n"
        "5. If the excerpts do not contain enough relevant information to answer the question, state clearly: "
        "'Based on your uploaded notes, I could not find sufficient information to answer this question.'"
    )

    async def answer_question(
        self,
        question: str,
        db: Session,
        document_ids: Optional[List[int]] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Answers a question using RAG over uploaded documents.
        Returns:
            Dict containing answer, source citations, and retrieval statistics.
        """
        start_time = time.perf_counter()
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Question cannot be empty.")

        normalized_question = normalize_query(clean_question)

        k = top_k or settings.RAG_TOP_K
        threshold = similarity_threshold if similarity_threshold is not None else settings.RAG_SIMILARITY_THRESHOLD

        # 1. Embed question locally (using normalized query for optimal semantic alignment)
        query_vec = embedding_service.embed_query(normalized_question)

        # 2. Search FAISS index
        raw_matches = vector_service.search(
            query_vector=query_vec,
            top_k=k,
            document_ids=document_ids,
            similarity_threshold=threshold
        )

        # 3. Handle case where no relevant chunks are retrieved
        if not raw_matches:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.info("No relevant document chunks found above similarity threshold.")
            return {
                "answer": "Based on your uploaded notes, I could not find relevant information to answer this question. Please make sure the topic is covered in your documents or try rephrasing.",
                "sources": [],
                "model": settings.OLLAMA_MODEL,
                "retrieval_count": 0,
                "duration_ms": round(elapsed_ms, 1)
            }

        # 4. Resolve document metadata for human-readable citations
        doc_ids_needed = list({m["document_id"] for m in raw_matches})
        docs = db.query(Document).filter(Document.id.in_(doc_ids_needed)).all()
        doc_map = {d.id: d.original_filename for d in docs}

        # 5. Build context excerpts and structured sources
        context_parts: List[str] = []
        sources: List[Dict[str, Any]] = []

        for idx, match in enumerate(raw_matches, 1):
            doc_name = doc_map.get(match["document_id"], f"Document #{match['document_id']}")
            page_num = match.get("page_number", 1)
            content = match["content"]

            context_parts.append(
                f"[Source {idx}: \"{doc_name}\", Page {page_num}]\n{content}"
            )

            sources.append({
                "document_id": match["document_id"],
                "document_name": doc_name,
                "page_number": page_num,
                "excerpt": content[:250] + ("..." if len(content) > 250 else ""),
                "similarity_score": match["similarity_score"]
            })

        formatted_context = "\n\n---\n\n".join(context_parts)

        # 6. Assemble prompt for Ollama
        prompt = (
            f"Here are the relevant excerpts from the student's study materials:\n\n"
            f"{formatted_context}\n\n"
            f"Student Question: {normalized_question}\n\n"
            f"Please provide a clear, accurate, and comprehensive explanation with page citations:"
        )

        # 7. Generate answer with local Ollama
        gen_result = await ollama_service.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=600
        )

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        reported_duration = gen_result.get("duration_ms") or total_elapsed_ms

        return {
            "answer": gen_result["response"],
            "sources": sources,
            "model": gen_result.get("model", settings.OLLAMA_MODEL),
            "retrieval_count": len(sources),
            "duration_ms": round(reported_duration, 1)
        }


rag_service = RAGService()
