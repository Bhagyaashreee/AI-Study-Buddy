import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.documents import RAGQueryRequest, RAGQueryResponse, RAGSourceItem
from app.services.rag_service import rag_service
from app.services.ollama_service import (
    OllamaConnectionException,
    OllamaTimeoutException,
    OllamaModelNotFoundException,
    OllamaResponseException,
)

logger = logging.getLogger("ai_study_buddy.api.chat")

router = APIRouter()


@router.post(
    "/ask",
    response_model=RAGQueryResponse,
    summary="Ask a question about uploaded notes (RAG)",
    description="Retrieves relevant document passages using FAISS local embeddings and generates an answer using local Ollama."
)
async def ask_notes_rag(
    request: RAGQueryRequest,
    db: Session = Depends(get_db)
) -> RAGQueryResponse:
    """RAG question-answering endpoint prioritizing user's uploaded materials with source citations."""
    try:
        result = await rag_service.answer_question(
            question=request.question,
            db=db,
            document_ids=request.document_ids,
            top_k=request.top_k
        )

        sources = [
            RAGSourceItem(
                document_id=s["document_id"],
                document_name=s["document_name"],
                page_number=s["page_number"],
                excerpt=s["excerpt"],
                similarity_score=s["similarity_score"]
            )
            for s in result.get("sources", [])
        ]

        return RAGQueryResponse(
            answer=result["answer"],
            sources=sources,
            model=result["model"],
            retrieval_count=result["retrieval_count"],
            duration_ms=result.get("duration_ms")
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except OllamaConnectionException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local Ollama service is unreachable. Please ensure Ollama is running."
        )
    except OllamaModelNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        )
    except OllamaTimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI inference timed out while generating the answer."
        )
    except OllamaResponseException:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Received an invalid response from the local AI service."
        )
    except Exception as exc:
        logger.error(f"Unexpected error answering RAG question: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while answering your question."
        )
