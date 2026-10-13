from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_empty_prompt_rejection():
    """Verify that empty prompts or whitespace-only prompts are rejected with 422."""
    # 1. Empty string
    response = client.post("/api/ai/chat", json={"prompt": ""})
    assert response.status_code == 422

    # 2. Whitespace only string
    response_ws = client.post("/api/ai/chat", json={"prompt": "   \n\t  "})
    assert response_ws.status_code == 422

    # 3. Missing prompt field
    response_missing = client.post("/api/ai/chat", json={})
    assert response_missing.status_code == 422


@pytest.mark.asyncio
async def test_successful_ai_generation_mocked():
    """Verify successful AI chat generation with mocked Ollama HTTP response."""
    mock_payload = {
        "response": "Photosynthesis is the process by which green plants convert light into chemical energy.",
        "model": "llama3.2:3b",
        "total_duration": 450000000,
        "eval_count": 15,
        "done": True
    }
    dummy_req = httpx.Request("POST", "http://localhost:11434/api/generate")
    mock_resp = httpx.Response(200, json=mock_payload, request=dummy_req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        response = client.post(
            "/api/ai/chat",
            json={"prompt": "Explain photosynthesis briefly."}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == mock_payload["response"]
        assert data["model"] == "llama3.2:3b"
        assert data["duration_ms"] == 450.0
        assert data["eval_count"] == 15
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_ollama_connection_failure():
    """Verify that connection failure to Ollama returns 503 without leaking stack traces."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        response = client.post(
            "/api/ai/chat",
            json={"prompt": "Hello there"}
        )

        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "unreachable" in data["detail"].lower()
        # Verify sensitive internal host/port is not exposed
        assert "http://127.0.0.1:11434" not in data["detail"]


@pytest.mark.asyncio
async def test_ollama_request_timeout():
    """Verify that inference timeout returns 504 Gateway Timeout."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timed out after 60s")

        response = client.post(
            "/api/ai/chat",
            json={"prompt": "Summarize this entire 500-page book."}
        )

        assert response.status_code == 504
        data = response.json()
        assert "timed out" in data["detail"].lower()


@pytest.mark.asyncio
async def test_ollama_malformed_response():
    """Verify that missing 'response' field returns 502 Bad Gateway."""
    dummy_req = httpx.Request("POST", "http://localhost:11434/api/generate")
    # Missing 'response' key
    mock_resp = httpx.Response(200, json={"error": "unexpected format", "some_data": 123}, request=dummy_req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        response = client.post(
            "/api/ai/chat",
            json={"prompt": "Test malformed"}
        )

        assert response.status_code == 502
        data = response.json()
        assert "malformed" in data["detail"].lower() or "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_ollama_status_endpoint_ready():
    """Verify /api/ai/status returns 'ready' when server is reachable and model is installed."""
    mock_tags = {
        "models": [
            {"name": "llama3.2:3b", "size": 2019393189},
            {"name": "qwen2.5:3b", "size": 1929912432}
        ]
    }
    dummy_req = httpx.Request("GET", "http://localhost:11434/api/tags")
    mock_resp = httpx.Response(200, json=mock_tags, request=dummy_req)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        response = client.get("/api/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["server_reachable"] is True
        assert data["model_installed"] is True
        assert data["target_model"] == "llama3.2:3b"
        assert "llama3.2:3b" in data["available_models"]


@pytest.mark.asyncio
async def test_ollama_status_endpoint_model_missing():
    """Verify /api/ai/status returns 'model_missing' when server is up but target model is missing."""
    mock_tags = {
        "models": [
            {"name": "other_model:latest", "size": 1000000}
        ]
    }
    dummy_req = httpx.Request("GET", "http://localhost:11434/api/tags")
    mock_resp = httpx.Response(200, json=mock_tags, request=dummy_req)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        response = client.get("/api/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "model_missing"
        assert data["server_reachable"] is True
        assert data["model_installed"] is False
        assert "ollama pull" in data["message"].lower()


@pytest.mark.asyncio
async def test_ollama_status_endpoint_offline():
    """Verify /api/ai/status returns 'offline' when Ollama is unreachable."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Ollama offline")

        response = client.get("/api/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "offline"
        assert data["server_reachable"] is False
        assert data["model_installed"] is False
