import os
import uuid
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.models.models import Document, DocumentChunk
from app.schemas.documents import (
    DocumentResponse,
    DocumentListResponse,
    DeleteDocumentResponse,
)
from app.services.pdf_service import (
    pdf_service,
    PDFCorruptedError,
    PDFEmptyError,
    PDFProcessingException,
)
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service

logger = logging.getLogger("ai_study_buddy.api.documents")

router = APIRouter()


def sanitize_filename(filename: str) -> str:
    """Strips path traversal elements and normalizes filename."""
    base = os.path.basename(filename)
    # Strip any directory separators or null bytes
    clean = base.replace("/", "").replace("\\", "").replace("\0", "")
    return clean.strip() or "document.pdf"


def to_doc_response(doc: Document, chunk_count: Optional[int] = None) -> DocumentResponse:
    """Helper to convert ORM model to Pydantic schema without exposing internal file paths."""
    count = chunk_count if chunk_count is not None else len(doc.chunks)
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size_bytes=doc.file_size_bytes,
        page_count=doc.page_count,
        status=doc.status,
        status_message=doc.status_message,
        chunk_count=count,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a PDF note or textbook",
    description="Uploads a PDF file, extracts text, chunks content, creates local embeddings, and indexes in FAISS."
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """Uploads and processes a PDF document with zero-cost local retrieval indexing."""
    original_name = sanitize_filename(file.filename or "uploaded.pdf")

    # 1. Validate file extension
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents (.pdf) are supported."
        )

    # 2. Read file content and enforce size limits
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed upload size of {max_mb} MB."
        )

    # 3. Validate PDF magic bytes '%PDF-'
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format: file does not have a valid PDF header."
        )

    # 4. Generate safe unique filename to avoid path traversal and name collisions
    unique_filename = f"{uuid.uuid4().hex}.pdf"
    storage_path = settings.UPLOAD_DIR / unique_filename

    # Save to disk
    try:
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with open(storage_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        logger.error(f"Failed to save file to disk: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file to local storage."
        )

    # 5. Create initial record in SQLite
    doc_record = Document(
        filename=unique_filename,
        original_filename=original_name,
        file_path=str(storage_path),
        file_size_bytes=file_size,
        page_count=0,
        status="processing",
        status_message="Extracting text and chunking..."
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # 6. Extract text and detect scanned PDFs
    try:
        pages_data, page_count, is_scanned = pdf_service.extract_text_by_pages(content)
        doc_record.page_count = page_count

        if is_scanned:
            doc_record.status = "scanned_pdf_no_ocr"
            doc_record.status_message = (
                "Scanned or image-only PDF detected. OCR is not currently supported in this "
                "zero-cost offline version. Please upload text-based PDFs."
            )
            db.commit()
            db.refresh(doc_record)
            return to_doc_response(doc_record, chunk_count=0)

        # 7. Chunk text
        chunks_data = pdf_service.chunk_document(
            pages_data,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        if not chunks_data:
            doc_record.status = "scanned_pdf_no_ocr"
            doc_record.status_message = "No text could be extracted from this document."
            db.commit()
            db.refresh(doc_record)
            return to_doc_response(doc_record, chunk_count=0)

        # 8. Persist chunks in SQLite
        db_chunks: List[DocumentChunk] = []
        for ch in chunks_data:
            chunk_obj = DocumentChunk(
                document_id=doc_record.id,
                chunk_index=ch["chunk_index"],
                page_number=ch["page_number"],
                content=ch["content"],
                char_count=ch["char_count"]
            )
            db.add(chunk_obj)
            db_chunks.append(chunk_obj)

        db.commit()
        for ch_obj in db_chunks:
            db.refresh(ch_obj)

        # 9. Generate local embeddings
        texts_to_embed = [ch.content for ch in db_chunks]
        embeddings = embedding_service.embed_texts(texts_to_embed)

        # 10. Index in FAISS
        faiss_data = [
            {
                "id": ch.id,
                "document_id": doc_record.id,
                "page_number": ch.page_number,
                "content": ch.content
            }
            for ch in db_chunks
        ]
        vector_service.add_chunks(faiss_data, embeddings)

        # 11. Mark document as ready
        doc_record.status = "ready"
        doc_record.status_message = f"Indexed {len(db_chunks)} chunks successfully."
        db.commit()
        db.refresh(doc_record)

        return to_doc_response(doc_record, chunk_count=len(db_chunks))

    except (PDFCorruptedError, PDFEmptyError) as exc:
        doc_record.status = "failed"
        doc_record.status_message = str(exc)
        db.commit()
        # Clean up file on disk
        if storage_path.exists():
            storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    except Exception as exc:
        logger.error(f"Error during document processing: {exc}", exc_info=True)
        doc_record.status = "failed"
        doc_record.status_message = "An error occurred while indexing document text."
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete document text extraction and vector indexing."
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all uploaded documents",
    description="Returns metadata and processing status for all uploaded notes."
)
def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    """Lists all uploaded documents with chunk counts."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    results = [to_doc_response(d) for d in docs]
    return DocumentListResponse(
        documents=results,
        total_documents=len(results)
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Retrieves metadata for a specific uploaded document."
)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentResponse:
    """Retrieves document metadata by ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document #{document_id} not found."
        )
    return to_doc_response(doc)


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document",
    description="Safely removes document, vector embeddings, chunks, and storage files."
)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> DeleteDocumentResponse:
    """Safely removes a document and synchronizes FAISS vector store."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document #{document_id} not found."
        )

    # 1. Remove vector embeddings from FAISS
    vectors_removed = vector_service.delete_document_vectors(document_id)

    # 2. Remove physical file from disk
    file_path = Path(doc.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as exc:
            logger.warning(f"Failed to remove file {file_path}: {exc}")

    # 3. Remove document from database (cascades chunks, quizzes, flashcards)
    db.delete(doc)
    db.commit()

    return DeleteDocumentResponse(
        success=True,
        document_id=document_id,
        message=f"Document '{doc.original_filename}' and its vectors were deleted successfully.",
        chunks_removed=vectors_removed
    )
