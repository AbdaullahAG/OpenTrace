"""Orchestrates topic classification: batches titles, calls the LLM,
and safely parses whatever comes back.

Small local models don't always return clean JSON — this module safely
extracts classifications with retries, concurrent processing, and flexible timeout.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.constants import (
    CLASSIFICATION_BATCH_SIZE,
    CLASSIFICATION_DEADLINE_SECONDS,
    CLASSIFICATION_MAX_RETRIES,
    CLASSIFICATION_MAX_WORKERS,
    CLASSIFICATION_RETRY_BACKOFF_SECONDS,
    TOPIC_CATEGORIES,
)
from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompts import build_topic_classification_prompt

_FALLBACK_TOPIC = "other"
_CACHE_MIN_OCCURRENCES = 2


def classify_topics(
    client: OllamaClient,
    titles: list[str],
    *,
    channels: list[str] | None = None,
) -> list[str]:
    """Classify titles into topic categories with caching and thread-pooling."""
    if channels and len(channels) != len(titles):
        channels = None

    channel_cache: dict[str, str] = {}
    labels: list[str | None] = [None] * len(titles)

    # ── Pass 1: Serve already-cached channels without hitting LLM ──
    if channels:
        channel_counts = Counter(
            ch for ch in channels if ch and ch != "Unknown"
        )
        pending_indices: list[int] = []
        seen_channels: set[str] = set()
        for i, (title, ch) in enumerate(zip(titles, channels)):
            if ch and ch != "Unknown" and channel_counts[ch] >= _CACHE_MIN_OCCURRENCES:
                if ch in channel_cache:
                    labels[i] = channel_cache[ch]
                elif ch in seen_channels:
                    pass
                else:
                    pending_indices.append(i)
                    seen_channels.add(ch)
            else:
                pending_indices.append(i)
    else:
        pending_indices = list(range(len(titles)))

    # ── Pass 2: Classify pending titles in parallel batches ──
    pending_titles = [titles[i] for i in pending_indices]
    batches = [
        (i, pending_titles[i : i + CLASSIFICATION_BATCH_SIZE])
        for i in range(0, len(pending_titles), CLASSIFICATION_BATCH_SIZE)
    ]

    deadline = time.time() + CLASSIFICATION_DEADLINE_SECONDS
    results_map: dict[int, list[str]] = {}

    def _process_batch(batch_idx: int, batch_titles: list[str]) -> tuple[int, list[str]]:
        if time.time() > deadline:
            return batch_idx, [_FALLBACK_TOPIC] * len(batch_titles)
        return batch_idx, _classify_batch_with_retry(client, batch_titles)

    with ThreadPoolExecutor(max_workers=CLASSIFICATION_MAX_WORKERS) as executor:
        futures = [
            executor.submit(_process_batch, idx, batch) for idx, batch in batches
        ]
        for future in as_completed(futures):
            try:
                batch_idx, batch_labels = future.result()
                results_map[batch_idx] = batch_labels
            except Exception as exc:
                print(f"⚠️ classifier: unexpected worker error: {exc}", file=sys.stderr)

    # Reconstruct labels in original order
    pending_labels: list[str] = []
    for i in range(0, len(pending_titles), CLASSIFICATION_BATCH_SIZE):
        batch_res = results_map.get(i, [_FALLBACK_TOPIC] * min(CLASSIFICATION_BATCH_SIZE, len(pending_titles) - i))
        pending_labels.extend(batch_res)

    # ── Pass 3: Write LLM labels back + populate channel cache ──
    for i, label in zip(pending_indices, pending_labels):
        labels[i] = label
        if channels:
            ch = channels[i]
            if ch and ch != "Unknown" and ch not in channel_cache:
                if channel_counts.get(ch, 0) >= _CACHE_MIN_OCCURRENCES: # type: ignore[union-attr]
                    # Never cache 'other' for a channel if we can avoid it
                    if label != _FALLBACK_TOPIC:
                        channel_cache[ch] = label

    # ── Pass 4: Back-fill cached labels for remaining slots ──
    if channels:
        for i, (label, ch) in enumerate(zip(labels, channels)):
            if label is None and ch in channel_cache:
                labels[i] = channel_cache[ch]

    final = [l if l is not None else _FALLBACK_TOPIC for l in labels]
    return final


def _classify_batch_with_retry(client: OllamaClient, titles: list[str]) -> list[str]:
    """Execute classification with exponential backoff on retries."""
    prompt = build_topic_classification_prompt(titles)

    for attempt in range(CLASSIFICATION_MAX_RETRIES + 1):
        try:
            raw_response = client.generate(prompt, timeout=90)
            parsed = _extract_json(raw_response)
            labels = parsed.get("classifications", [])

            # Filter valid labels
            valid_labels = [
                lbl if lbl in TOPIC_CATEGORIES else _FALLBACK_TOPIC
                for lbl in labels
            ]

            if len(valid_labels) >= len(titles):
                return valid_labels[: len(titles)]
            
            # If partial response, pad with fallback
            valid_labels.extend([_FALLBACK_TOPIC] * (len(titles) - len(valid_labels)))
            return valid_labels

        except (OllamaError, Exception) as exc:
            if attempt < CLASSIFICATION_MAX_RETRIES:
                time.sleep(CLASSIFICATION_RETRY_BACKOFF_SECONDS * (attempt + 1))
            else:
                print(f"⚠️ classifier: batch failed after {CLASSIFICATION_MAX_RETRIES} retries: {exc}", file=sys.stderr)

    return [_FALLBACK_TOPIC] * len(titles)


def _extract_json(text: str) -> dict:
    """Find and parse first balanced JSON block."""
    for candidate in _balanced_brace_blocks(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    for candidate in _balanced_bracket_blocks(text):
        try:
            arr = json.loads(candidate)
            if isinstance(arr, list):
                return {"classifications": arr}
        except json.JSONDecodeError:
            continue

    return {}


def _balanced_brace_blocks(text: str):
    """Yield top-level {...} blocks."""
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
                yield text[start : i + 1]


def _balanced_bracket_blocks(text: str):
    """Yield top-level [...] blocks."""
    depth = 0
    start = None
    for i, char in enumerate(text):
        if char == "[":
            if depth == 0:
                start = i
            depth += 1
        elif char == "]" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start : i + 1]