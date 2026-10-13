from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: str = Field(..., description="Status of the SQLite database connection: 'connected' or 'disconnected'")
    type: str = "sqlite"


class OllamaHealth(BaseModel):
    status: str = Field(..., description="'available' or 'unavailable'")
    base_url: str
    target_model: str
    model_installed: bool = False
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status: 'healthy', 'degraded', or 'unhealthy'")
    project_name: str
    version: str
    environment: str
    database: DatabaseHealth
    ollama: OllamaHealth
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
