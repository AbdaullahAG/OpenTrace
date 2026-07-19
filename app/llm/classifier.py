"""Orchestrates topic classification: batches titles, calls the LLM,
and safely parses whatever comes back.

Small local models don't always return clean JSON — this is the one
place that has to assume the model's output is unreliable and never
trust it blindly (no eval(), no assuming well-formed JSON).
"""

from __future__ import annotations

import json
import re

from app.constants import CLASSIFICATION_BATCH_SIZE, TOPIC_CATEGORIES
from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompts import build_topic_classification_prompt

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_FALLBACK_TOPIC = "other"


def classify_topics(client: OllamaClient, titles: list[str]) -> dict[str, int]:
    """Classify a list of titles into topic categories.

    Returns a plain count per category, e.g. {"sports": 12, "news": 4}.
    Never raises — on any failure (Ollama down, bad output) the
    unclassified titles simply fall into "other" so the caller can
    keep going with a degraded-but-honest result.
    """
    counts = {topic: 0 for topic in TOPIC_CATEGORIES}

    for start in range(0, len(titles), CLASSIFICATION_BATCH_SIZE):
        batch = titles[start:start + CLASSIFICATION_BATCH_SIZE]
        labels = _classify_batch(client, batch)
        for label in labels:
            counts[label if label in counts else _FALLBACK_TOPIC] += 1

    return counts


def _classify_batch(client: OllamaClient, titles: list[str]) -> list[str]:
    prompt = build_topic_classification_prompt(titles)

    try:
        raw_response = client.generate(prompt)
    except OllamaError:
        return [_FALLBACK_TOPIC] * len(titles)

    parsed = _extract_json(raw_response)
    labels = parsed.get("classifications", [])

    if len(labels) < len(titles):
        labels += [_FALLBACK_TOPIC] * (len(titles) - len(labels))

    return labels[:len(titles)]


def _extract_json(text: str) -> dict:
    """Small models sometimes wrap JSON in explanatory text. Pull the
    first {...} block out and parse just that.
    """
    match = _JSON_BLOCK.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}
