import io
from unittest.mock import AsyncMock, patch
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.database.session import SessionLocal, init_db
from app.models.models import Document, DocumentChunk
from tests.pdf_helpers import generate_test_pdf

client = TestClient(app)


def setup_module(module):
    """Ensure database and vector store are initialized."""
    init_db()


def test_embedding_dimensions_and_normalization():
    """Verify local embedding model produces 384-dimensional normalized vectors."""
    texts = [
        "Artificial intelligence is transforming education.",
        "Retrieval Augmented Generation reduces language model hallucinations."
    ]
    embeddings = embedding_service.embed_texts(texts)
    assert embeddings.shape == (2, 384)
    assert embeddings.dtype == np.float32

    # Verify L2 normalization (norm should be ~1.0)
    for vec in embeddings:
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-4

    # Single query embedding
    query_emb = embedding_service.embed_query("What is machine learning?")
    assert query_emb.shape == (1, 384)
    assert abs(np.linalg.norm(query_emb[0]) - 1.0) < 1e-4


def test_multi_document_indexing_and_retrieval():
    """Verify FAISS indexes multiple documents and supports document-level filtering."""
    # 1. Upload Doc 1 (Astronomy)
    pdf1 = generate_test_pdf(["Jupiter is the largest planet in our solar system. It has a Great Red Spot."])
    files1 = {"file": ("astronomy.pdf", io.BytesIO(pdf1), "application/pdf")}
    resp1 = client.post("/api/documents/upload", files=files1)
    assert resp1.status_code == 201
    doc1_id = resp1.json()["id"]

    # 2. Upload Doc 2 (Chemistry)
    pdf2 = generate_test_pdf(["Water consists of two hydrogen atoms bonded to one oxygen atom."])
    files2 = {"file": ("chemistry.pdf", io.BytesIO(pdf2), "application/pdf")}
    resp2 = client.post("/api/documents/upload", files=files2)
    assert resp2.status_code == 201
    doc2_id = resp2.json()["id"]

    try:
        # Search for astronomy query
        q_vec = embedding_service.embed_query("What is the largest planet?")
        results = vector_service.search(q_vec, top_k=2)
        assert len(results) > 0
        assert results[0]["document_id"] == doc1_id

        # Search with document filter restricting to doc 2
        filtered_results = vector_service.search(q_vec, top_k=2, document_ids=[doc2_id])
        for r in filtered_results:
            assert r["document_id"] == doc2_id

    finally:
        # Clean up
        client.delete(f"/api/documents/{doc1_id}")
        client.delete(f"/api/documents/{doc2_id}")


def test_index_rebuild_from_database():
    """Verify FAISS index can be completely rebuilt from SQLite chunks."""
    # 1. Upload a document
    pdf = generate_test_pdf(["The speed of light in vacuum is approximately 299,792,458 meters per second."])
    files = {"file": ("physics.pdf", io.BytesIO(pdf), "application/pdf")}
    resp = client.post("/api/documents/upload", files=files)
    doc_id = resp.json()["id"]

    db = SessionLocal()
    try:
        # Rebuild index
        count = vector_service.rebuild_index_from_db(db)
        assert count > 0
        assert vector_service.index.ntotal >= count

        # Verify search still works after rebuild
        q_vec = embedding_service.embed_query("speed of light")
        matches = vector_service.search(q_vec, top_k=1)
        assert len(matches) > 0
        assert matches[0]["document_id"] == doc_id
    finally:
        db.close()
        client.delete(f"/api/documents/{doc_id}")


@pytest.mark.asyncio
async def test_rag_ask_endpoint_with_citations():
    """Verify /api/chat/ask retrieves context and returns source citations."""
    pdf = generate_test_pdf([
        "DNA is a polymer composed of two polynucleotide chains that coil around each other to form a double helix.",
        "The nitrogenous bases in DNA are Adenine, Thymine, Guanine, and Cytosine."
    ])
    files = {"file": ("genetics.pdf", io.BytesIO(pdf), "application/pdf")}
    upload_res = client.post("/api/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    mock_llm_reply = {
        "response": "DNA is composed of two polynucleotide chains forming a double helix, with bases A, T, G, and C.",
        "model": "llama3.2:3b",
        "total_duration": 300000000,
        "eval_count": 20,
        "done": True
    }
    dummy_req = httpx.Request("POST", "http://localhost:11434/api/generate")
    mock_resp = httpx.Response(200, json=mock_llm_reply, request=dummy_req)

    try:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            response = client.post(
                "/api/chat/ask",
                json={
                    "question": "What is DNA composed of?",
                    "document_ids": [doc_id]
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == mock_llm_reply["response"]
            assert data["retrieval_count"] > 0
            assert len(data["sources"]) > 0

            # Check citation details
            citation = data["sources"][0]
            assert citation["document_id"] == doc_id
            assert citation["document_name"] == "genetics.pdf"
            assert citation["page_number"] in [1, 2]
            assert "similarity_score" in citation
            assert len(citation["excerpt"]) > 0

    finally:
        client.delete(f"/api/documents/{doc_id}")


def test_rag_out_of_scope_query():
    """Verify that completely irrelevant query returns graceful fallback without LLM hallucinations."""
    # When no document matches above the threshold (or searching with non-existent document ID)
    response = client.post(
        "/api/chat/ask",
        json={
            "question": "What is the capital of Mars?",
            "document_ids": [999999]  # Non-existent doc
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "could not find" in data["answer"].lower()
    assert data["retrieval_count"] == 0
    assert len(data["sources"]) == 0


@pytest.mark.asyncio
async def test_rag_ollama_failure_handling():
    """Verify that Ollama connection error during RAG answer generation returns 503."""
    pdf = generate_test_pdf(["Calculus is the mathematical study of continuous change."])
    upload_res = client.post("/api/documents/upload", files={"file": ("math.pdf", io.BytesIO(pdf), "application/pdf")})
    doc_id = upload_res.json()["id"]

    try:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Ollama down")

            response = client.post(
                "/api/chat/ask",
                json={"question": "What is calculus?", "document_ids": [doc_id]}
            )
            assert response.status_code == 503
            assert "unreachable" in response.json()["detail"].lower()
    finally:
        client.delete(f"/api/documents/{doc_id}")
