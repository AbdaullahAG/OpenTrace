"""Orchestrates topic classification: batches titles, calls the LLM,
and safely parses whatever comes back.

Small local models don't always return clean JSON — this is the one
place that has to assume the model's output is unreliable and never
trust it blindly (no eval(), no assuming well-formed JSON).
"""

from __future__ import annotations

import json
import sys

from app.constants import CLASSIFICATION_BATCH_SIZE, TOPIC_CATEGORIES
from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompts import build_topic_classification_prompt

_FALLBACK_TOPIC = "other"


def classify_topics(client: OllamaClient, titles: list[str]) -> list[str]:
    """Classify titles into topic categories, one label per title, in
    the same order as the input.

    Never raises — on any failure (Ollama down, bad output) the
    affected titles simply get "other" so the caller can keep going
    with a degraded-but-honest result.
    """
    labels: list[str] = []
    for start in range(0, len(titles), CLASSIFICATION_BATCH_SIZE):
        batch = titles[start:start + CLASSIFICATION_BATCH_SIZE]
        batch_labels = _classify_batch(client, batch)
        labels.extend(
            label if label in TOPIC_CATEGORIES else _FALLBACK_TOPIC
            for label in batch_labels
        )
    return labels


def _classify_batch(client: OllamaClient, titles: list[str]) -> list[str]:
    prompt = build_topic_classification_prompt(titles)

    try:
        raw_response = client.generate(prompt, timeout=90)
    except OllamaError as exc:
        print(f"⚠️ classifier: batch of {len(titles)} failed, falling back to 'other': {exc}", file=sys.stderr)
        return [_FALLBACK_TOPIC] * len(titles)

    parsed = _extract_json(raw_response)
    labels = parsed.get("classifications", [])

    if len(labels) < len(titles):
        labels += [_FALLBACK_TOPIC] * (len(titles) - len(labels))

    return labels[:len(titles)]


def _extract_json(text: str) -> dict:
    """Find the first *parseable* balanced {...} object in the text.

    A greedy regex (\\{.*\\}) grabs from the FIRST '{' to the LAST '}'
    in the whole response — if the model echoes part of the prompt
    (which itself contains an example JSON object), that spans across
    both and produces invalid JSON. Scanning brace depth instead finds
    each well-formed object in order and tries them one at a time,
    since the model may echo a non-JSON `{...}` fragment before the
    real answer.
    """
    for candidate in _balanced_brace_blocks(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    print(f"⚠️ classifier: no parseable JSON object in model output: {text[:120]!r}", file=sys.stderr)
    return {}


def _balanced_brace_blocks(text: str):
    """Yield every top-level {...} substring, in order of appearance."""
    depth = 0
    start = None
    for i, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start:i + 1]
