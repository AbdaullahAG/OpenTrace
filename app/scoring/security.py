"""Input validation and sanitization.

Everything here runs before user data touches the LLM or the scoring
math. Two concrete threats this guards against:

1. Prompt injection — a crafted video title like
   "ignore previous instructions and..." ending up inside an LLM prompt.
2. Resource exhaustion — a huge export file turning into a huge batch
   of requests to Ollama, or one absurdly long string breaking a prompt.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.constants import MAX_ITEMS_PER_REQUEST, MAX_TITLE_LENGTH

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_input(value: str) -> str:
    """Strip control characters and cap length. Safe to embed in a prompt."""
    if not isinstance(value, str):
        return ""
    cleaned = _CONTROL_CHARS.sub("", value).strip()
    return cleaned[:MAX_TITLE_LENGTH]


def sanitize_items(items: list[dict]) -> list[dict]:
    """Clean a batch of feed items: drop malformed entries, sanitize text
    fields, and cap the batch size before anything reaches the LLM.
    """
    if not isinstance(items, list):
        return []

    cleaned: list[dict] = []
    for item in items[:MAX_ITEMS_PER_REQUEST]:
        if not isinstance(item, dict):
            continue
        title = sanitize_input(item.get("title", ""))
        channel = sanitize_input(item.get("channel", ""))
        if not title and not channel:
            continue  # nothing usable in this entry

        cleaned.append({
            **item,
            "title": title,
            "channel": channel,
        })

    return cleaned


def is_local_host(url: str) -> bool:
    """Check that a host string points to localhost.

    OpenTrace's entire privacy claim rests on the LLM running locally.
    Call this on `settings.ollama_host` at startup and warn loudly if
    it ever points somewhere else.
    """
    try:
        hostname = urlparse(url).hostname or ""
    except ValueError:
        return False
    return hostname in {"localhost", "127.0.0.1", "::1"}
