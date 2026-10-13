from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class DocumentResponse(BaseModel):
    """Metadata response for an uploaded document."""
    id: int
    filename: str
    original_filename: str
    file_size_bytes: int
    page_count: int
    status: str
    status_message: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """List of uploaded documents."""
    documents: List[DocumentResponse]
    total_documents: int


class DeleteDocumentResponse(BaseModel):
    """Response confirming safe document deletion."""
    success: bool
    document_id: int
    message: str
    chunks_removed: int


class RAGSourceItem(BaseModel):
    """Supporting citation excerpt from study notes."""
    document_id: int
    document_name: str
    page_number: int
    excerpt: str
    similarity_score: float


class RAGQueryRequest(BaseModel):
    """Request model for asking questions against study notes."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to ask about uploaded study notes."
    )
    document_ids: Optional[List[int]] = Field(
        None,
        description="Optional list of document IDs to restrict search to."
    )
    top_k: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Maximum number of context chunks to retrieve."
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Question cannot be empty or only whitespace.")
        return clean


class RAGQueryResponse(BaseModel):
    """RAG answer with supporting citations."""
    answer: str
    sources: List[RAGSourceItem]
    model: str
    retrieval_count: int
    duration_ms: Optional[float] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
