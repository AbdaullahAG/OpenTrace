from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"

load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    debug: bool = True
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    app_port: int = 8000


def get_settings() -> Settings:
    return Settings(
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"},
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "mistral"),
        app_port=int(os.getenv("APP_PORT", "8000")),
    )
