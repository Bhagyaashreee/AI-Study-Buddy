import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.pdf_service import pdf_service, PDFCorruptedError, PDFEmptyError
from tests.pdf_helpers import generate_test_pdf
from app.database.session import SessionLocal, init_db
from app.models.models import Document, DocumentChunk
from app.services.vector_service import vector_service

client = TestClient(app)


def setup_module(module):
    """Ensure database tables exist before running document tests."""
    init_db()


def test_pdf_extraction_and_chunking():
    """Verify PyPDF page-by-page extraction and chunking preserves 1-based page numbers."""
    pages = [
        "Cell biology is the study of cell structure and function. Cells are the fundamental units of life.",
        "Mitochondria generate most of the chemical energy needed to power the biochemical reactions of the cell."
    ]
    pdf_bytes = generate_test_pdf(pages)
    pages_data, page_count, is_scanned = pdf_service.extract_text_by_pages(pdf_bytes)

    assert page_count == 2
    assert is_scanned is False
    assert len(pages_data) == 2
    assert pages_data[0]["page_number"] == 1
    assert "Cell biology" in pages_data[0]["text"]
    assert pages_data[1]["page_number"] == 2
    assert "Mitochondria" in pages_data[1]["text"]

    chunks = pdf_service.chunk_document(pages_data, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2
    # Verify sequential chunk indices and valid page numbers
    for idx, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == idx
        assert chunk["page_number"] in [1, 2]
        assert len(chunk["content"]) > 0


def test_empty_and_corrupted_pdf_rejection():
    """Verify corrupted and zero-byte PDFs raise appropriate errors."""
    with pytest.raises(PDFEmptyError):
        pdf_service.extract_text_by_pages(b"")

    with pytest.raises(PDFCorruptedError):
        pdf_service.extract_text_by_pages(b"Not a PDF file at all")


def test_scanned_pdf_detection():
    """Verify image-only or low-text PDFs are flagged as scanned."""
    # PDF with barely 5 characters across all pages
    minimal_pdf = generate_test_pdf(["Hi"])
    _, _, is_scanned = pdf_service.extract_text_by_pages(minimal_pdf)
    assert is_scanned is True


def test_document_upload_and_lifecycle():
    """Test full document upload, listing, get, and delete workflow."""
    pages = [
        "Photosynthesis takes place in chloroplasts, which contain chlorophyll.",
        "Light-dependent reactions convert solar energy into chemical energy in the thylakoid membranes."
    ]
    pdf_bytes = generate_test_pdf(pages)

    # 1. Upload Document
    files = {"file": ("biology_notes.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 201
    doc_data = response.json()
    doc_id = doc_data["id"]

    assert doc_data["original_filename"] == "biology_notes.pdf"
    assert doc_data["page_count"] == 2
    assert doc_data["status"] == "ready"
    assert doc_data["chunk_count"] > 0
    # Verify internal file paths are NOT exposed
    assert "file_path" not in doc_data

    # 2. List Documents
    list_resp = client.get("/api/documents")
    assert list_resp.status_code == 200
    all_docs = list_resp.json()
    assert all_docs["total_documents"] >= 1
    assert any(d["id"] == doc_id for d in all_docs["documents"])

    # 3. Get Document by ID
    get_resp = client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 200
    single_doc = get_resp.json()
    assert single_doc["id"] == doc_id
    assert single_doc["original_filename"] == "biology_notes.pdf"

    # 4. Check FAISS Vector Count
    assert vector_service.index.ntotal > 0

    # 5. Delete Document
    del_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["success"] is True
    assert del_data["document_id"] == doc_id
    assert del_data["chunks_removed"] > 0

    # 6. Verify Document is gone from DB
    get_after_del = client.get(f"/api/documents/{doc_id}")
    assert get_after_del.status_code == 404


def test_upload_invalid_file_types():
    """Verify non-PDF uploads are rejected with 400."""
    files = {"file": ("notes.txt", io.BytesIO(b"Just plain text"), "text/plain")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "only pdf" in response.json()["detail"].lower()


def test_upload_empty_pdf_rejected():
    """Verify 0-byte PDF upload is rejected with 400."""
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
