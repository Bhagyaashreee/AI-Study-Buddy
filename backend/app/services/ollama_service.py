import json
import logging
from typing import Optional, Dict, Any, List
import httpx
from app.core.config import settings

logger = logging.getLogger("ai_study_buddy.ollama")


class OllamaServiceException(Exception):
    """Base exception for Ollama service errors."""
    pass


class OllamaConnectionException(OllamaServiceException):
    """Raised when the Ollama server cannot be reached."""
    pass


class OllamaTimeoutException(OllamaServiceException):
    """Raised when an Ollama request times out."""
    pass


class OllamaModelNotFoundException(OllamaServiceException):
    """Raised when the requested model is not pulled or installed."""
    pass


class OllamaResponseException(OllamaServiceException):
    """Raised when Ollama returns an error or malformed response."""
    pass


class OllamaService:
    """Service client for local Ollama HTTP API inference.
    Strictly zero-cost, local-only, never uses paid external APIs.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        keep_alive: Optional[str] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS
        self.keep_alive = keep_alive or getattr(settings, "OLLAMA_KEEP_ALIVE", "30m")

    async def check_status(self) -> Dict[str, Any]:
        """Check Ollama service reachability and model availability.
        Distinguishes between server reachable and configured model installed.
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=2.0)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code != 200:
                    return {
                        "server_reachable": False,
                        "model_installed": False,
                        "target_model": self.model,
                        "available_models": [],
                        "error_message": f"Ollama returned HTTP {response.status_code}."
                    }
                
                data = response.json()
                models = data.get("models", [])
                model_names: List[str] = [m.get("name", "") for m in models]
                
                # Check for exact name match or prefix match (e.g. 'llama3.2:3b' vs 'llama3.2:latest')
                target_base = self.model.split(":")[0]
                model_installed = any(
                    name == self.model or name.startswith(f"{target_base}:")
                    for name in model_names
                )
                
                error_msg = None
                if not model_installed:
                    error_msg = f"Configured model '{self.model}' is not pulled. Run 'ollama pull {self.model}'."

                return {
                    "server_reachable": True,
                    "model_installed": model_installed,
                    "target_model": self.model,
                    "available_models": model_names,
                    "error_message": error_msg
                }
        except httpx.ConnectError:
            return {
                "server_reachable": False,
                "model_installed": False,
                "target_model": self.model,
                "available_models": [],
                "error_message": "Local Ollama service is unreachable. Ensure Ollama is running."
            }
        except httpx.TimeoutException:
            return {
                "server_reachable": False,
                "model_installed": False,
                "target_model": self.model,
                "available_models": [],
                "error_message": "Connection to Ollama server timed out."
            }
        except Exception as exc:
            logger.warning(f"Unexpected error checking Ollama status: {exc}")
            return {
                "server_reachable": False,
                "model_installed": False,
                "target_model": self.model,
                "available_models": [],
                "error_message": "Unable to verify Ollama status."
            }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        format: Optional[str] = None,
        keep_alive: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a completion using the local Ollama model.
        Args:
            prompt: User prompt text.
            system_prompt: Optional instructions for the model.
            temperature: Generation temperature (0.0 - 1.0).
            max_tokens: Maximum tokens to generate.
            format: Optional format specification (e.g., 'json').
            keep_alive: Time to keep model loaded in memory (e.g., '30m').
        Returns:
            Dictionary with response text, model name, and timing statistics.
        Raises:
            OllamaConnectionException, OllamaTimeoutException,
            OllamaModelNotFoundException, OllamaResponseException
        """
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("Prompt must not be empty or whitespace only.")

        effective_keep_alive = keep_alive or self.keep_alive

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": clean_prompt,
            "stream": False,
            "keep_alive": effective_keep_alive,
            "options": {
                "temperature": max(0.0, min(1.0, temperature))
            }
        }

        if format and format.strip():
            payload["format"] = format.strip()

        if system_prompt and system_prompt.strip():
            payload["system"] = system_prompt.strip()

        if max_tokens and max_tokens > 0:
            payload["options"]["num_predict"] = max_tokens

        url = f"{self.base_url}/api/generate"
        client_timeout = httpx.Timeout(self.timeout, connect=5.0)

        try:
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 404:
                    raise OllamaModelNotFoundException(
                        f"Model '{self.model}' not found in Ollama. Run 'ollama pull {self.model}'."
                    )
                elif response.status_code != 200:
                    raise OllamaResponseException(
                        f"Ollama returned HTTP error status {response.status_code}."
                    )

                try:
                    data = response.json()
                except Exception as exc:
                    raise OllamaResponseException("Malformed JSON received from Ollama.") from exc

                if "response" not in data:
                    raise OllamaResponseException("Malformed Ollama response: missing 'response' field.")

                # Calculate duration in milliseconds if total_duration in nanoseconds is provided
                total_duration_ns = data.get("total_duration")
                duration_ms = (total_duration_ns / 1_000_000.0) if total_duration_ns else None

                return {
                    "response": data["response"],
                    "model": data.get("model", self.model),
                    "duration_ms": duration_ms,
                    "eval_count": data.get("eval_count"),
                    "done": data.get("done", True)
                }

        except httpx.ConnectError as exc:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {exc}")
            raise OllamaConnectionException(
                "Local Ollama service is unreachable. Please verify Ollama is running."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error(f"Ollama request timed out after {self.timeout}s: {exc}")
            raise OllamaTimeoutException(
                f"Local AI inference timed out after {self.timeout} seconds."
            ) from exc
        except (OllamaServiceException, ValueError):
            raise
        except Exception as exc:
            logger.error(f"Unexpected error communicating with Ollama: {exc}", exc_info=True)
            raise OllamaResponseException("An unexpected error occurred during local AI inference.") from exc


# Shared singleton instance
ollama_service = OllamaService()
