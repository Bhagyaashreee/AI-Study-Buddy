import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator
import httpx
from fastapi import FastAPI, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import init_db, check_db_connection, get_db
from app.schemas.health import HealthResponse, DatabaseHealth, OllamaHealth
from app.services.ollama_service import ollama_service
from app.api.ai import router as ai_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.quizzes import router as quizzes_router
from app.api.flashcards import router as flashcards_router
from app.api.progress import router as progress_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_study_buddy")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    logger.info("Initializing AI Study Buddy backend...")
    # Ensure all local storage folders exist
    settings.ensure_directories_exist()
    # Initialize SQLite database and tables
    try:
        init_db()
        logger.info("Database and tables initialized successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize database: {exc}")
    yield
    logger.info("AI Study Buddy backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Zero-Cost Local AI Learning Platform backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(ai_router, prefix="/api/ai", tags=["AI Inference"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat_router, prefix="/api/chat", tags=["RAG Chat"])
app.include_router(quizzes_router, prefix="/api/quizzes", tags=["Quizzes"])
app.include_router(flashcards_router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(progress_router, prefix="/api/progress", tags=["Study Progress"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safely catch unhandled errors without leaking internal system paths."""
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.get("/", tags=["General"])
async def root():
    """Root endpoint providing service information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "online",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health endpoint verifying application status, database connectivity, and local Ollama status."""
    # 1. Verify Database
    db_connected = check_db_connection()
    db_status = "connected" if db_connected else "disconnected"

    # 2. Check Ollama local service via service layer
    ollama_check = await ollama_service.check_status()
    server_reachable = ollama_check["server_reachable"]
    model_installed = ollama_check["model_installed"]
    ollama_status = "available" if (server_reachable and model_installed) else ("degraded" if server_reachable else "unavailable")

    # Determine overall status
    if not db_connected:
        overall_status = "unhealthy"
    elif not server_reachable or not model_installed:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        project_name=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        environment=settings.ENVIRONMENT,
        database=DatabaseHealth(
            status=db_status,
            type="sqlite"
        ),
        ollama=OllamaHealth(
            status=ollama_status,
            base_url=settings.OLLAMA_BASE_URL,
            target_model=settings.OLLAMA_MODEL,
            model_installed=model_installed,
            details=ollama_check.get("error_message") or f"{len(ollama_check.get('available_models', []))} local model(s) detected."
        ),
        timestamp=datetime.now(timezone.utc)
    )
