import logging
from fastapi import APIRouter, HTTPException, status
from app.services.ollama_service import (
    ollama_service,
    OllamaConnectionException,
    OllamaTimeoutException,
    OllamaModelNotFoundException,
    OllamaResponseException,
)
from app.schemas.ai import ChatRequest, ChatResponse, OllamaStatusResponse
from app.core.config import settings

logger = logging.getLogger("ai_study_buddy.api.ai")

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Generate AI response via local Ollama",
    description="Sends a prompt to the local Ollama LLM and returns the generated answer. Completely free and zero-cost."
)
async def generate_chat_response(request: ChatRequest) -> ChatResponse:
    """Chat endpoint communicating with local Ollama instance."""
    try:
        result = await ollama_service.generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        return ChatResponse(
            response=result["response"],
            model=result["model"],
            duration_ms=result.get("duration_ms"),
            eval_count=result.get("eval_count")
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except OllamaConnectionException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local Ollama service is unreachable. Please ensure Ollama is running locally."
        )
    except OllamaModelNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configured model '{settings.OLLAMA_MODEL}' is not installed in Ollama. Run 'ollama pull {settings.OLLAMA_MODEL}'."
        )
    except OllamaTimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Local AI inference timed out. Please try again with a simpler prompt."
        )
    except OllamaResponseException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid or malformed response from local Ollama service."
        )
    except Exception as exc:
        logger.error(f"Unexpected error in /api/ai/chat: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred."
        )


@router.get(
    "/status",
    response_model=OllamaStatusResponse,
    summary="Check local Ollama reachability and model availability",
    description="Reports whether Ollama is active and whether the configured model is installed locally."
)
async def get_ollama_status() -> OllamaStatusResponse:
    """Inspect local Ollama connectivity and installed models."""
    check = await ollama_service.check_status()
    
    if not check["server_reachable"]:
        state = "offline"
    elif not check["model_installed"]:
        state = "model_missing"
    else:
        state = "ready"

    return OllamaStatusResponse(
        status=state,
        server_reachable=check["server_reachable"],
        model_installed=check["model_installed"],
        target_model=check["target_model"],
        available_models=check.get("available_models", []),
        message=check.get("error_message") or "Ollama and target model are ready for local inference."
    )
