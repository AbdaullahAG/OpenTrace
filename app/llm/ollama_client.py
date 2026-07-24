"""Thin HTTP client for a local Ollama instance.

Deliberately dumb: no prompt building, no JSON parsing of model output.
That logic lives in classifier.py. This file only knows how to talk
to the Ollama HTTP API.
"""

from __future__ import annotations

import requests

from app.config import get_settings
from app.scoring.security import is_local_host

_TAGS_TIMEOUT = 3
_DEFAULT_GENERATE_TIMEOUT = 90  # CPU-only inference on longer prompts can take a while


class OllamaError(Exception):
    """Raised when Ollama is unreachable or returns an unusable response."""


class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None):
        settings = get_settings()
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model

        if not is_local_host(self.host):
            # Not a hard failure — some teammates may want a remote dev
            # server — but this breaks the "nothing leaves your device"
            # promise, so it must never happen silently.
            print(f"⚠️  OLLAMA_HOST is not local: {self.host}")

    def ping(self) -> bool:
        """Cheap connectivity check — doesn't require a model to be loaded."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=_TAGS_TIMEOUT)
            return response.ok
        except requests.exceptions.RequestException:
            return False

    def generate(self, prompt: str, *, temperature: float = 0.2, timeout: float = _DEFAULT_GENERATE_TIMEOUT) -> str:
        """Send a prompt, return the raw text response.

        Raises OllamaError on connection failure or timeout so callers
        can decide how to degrade gracefully instead of the app crashing.
        `timeout` is overridable per-call — a batch of 10 complex titles
        on CPU-only inference needs more room than a one-line prompt.
        """
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise OllamaError(
                f"Cannot reach Ollama at {self.host}. Is 'ollama serve' running?"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise OllamaError(
                f"Ollama request timed out after {timeout}s."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise OllamaError(f"Ollama returned an error: {exc}") from exc

        return response.json().get("response", "").strip()
