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
from dataclasses import dataclass

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


@dataclass
class ClassificationResult:
    """Structured outcome of classify_topics().

    The counters exist so a caller — or a human staring at a confusing
    report — can tell *why* items ended up as "other" without needing
    a separate diagnostic script: genuinely failed (bad model output /
    Ollama error) vs dropped because the time budget ran out vs served
    from the channel cache without ever touching the LLM.
    """
    labels: list[str]
    failed: int = 0
    deadline_dropped: int = 0
    cache_hits: int = 0
    elapsed_seconds: float = 0.0


def classify_topics(
    client: OllamaClient,
    titles: list[str],
    *,
    channels: list[str] | None = None,
) -> ClassificationResult:
    """Classify titles into topic categories with caching and thread-pooling."""
    start_time = time.time()

    if channels and len(channels) != len(titles):
        channels = None

    channel_cache: dict[str, str] = {}
    labels: list[str | None] = [None] * len(titles)
    channel_counts: Counter = Counter()

    # ── Pass 1: one representative per repeated channel goes to the LLM;
    # every other occurrence waits for Pass 4's cache backfill ──
    if channels:
        channel_counts = Counter(ch for ch in channels if ch and ch != "Unknown")
        pending_indices: list[int] = []
        seen_channels: set[str] = set()
        for i, ch in enumerate(channels):
            if ch and ch != "Unknown" and channel_counts[ch] >= _CACHE_MIN_OCCURRENCES:
                if ch in seen_channels:
                    continue  # resolved later via Pass 4 backfill
                pending_indices.append(i)
                seen_channels.add(ch)
            else:
                pending_indices.append(i)
    else:
        pending_indices = list(range(len(titles)))

    # ── Pass 2: classify pending titles, concurrently, batch by batch ──
    pending_titles = [titles[i] for i in pending_indices]
    batches = [
        (i, pending_titles[i : i + CLASSIFICATION_BATCH_SIZE])
        for i in range(0, len(pending_titles), CLASSIFICATION_BATCH_SIZE)
    ]

    deadline = time.time() + CLASSIFICATION_DEADLINE_SECONDS
    results_map: dict[int, tuple[list[str], int, int]] = {}  # idx -> (labels, failed, dropped)

    def _process_batch(batch_idx: int, batch_titles: list[str]) -> tuple[int, list[str], int, int]:
        if time.time() > deadline:
            return batch_idx, [_FALLBACK_TOPIC] * len(batch_titles), 0, len(batch_titles)
        batch_labels, failed = _classify_batch_with_retry(client, batch_titles)
        if time.time() > deadline:
            # The call eventually returned something, but only after
            # blowing past the time budget — treat it the same as never
            # having tried, so one slow batch can't silently exceed the
            # ceiling the deadline exists to enforce.
            return batch_idx, [_FALLBACK_TOPIC] * len(batch_titles), 0, len(batch_titles)
        return batch_idx, batch_labels, failed, 0

    with ThreadPoolExecutor(max_workers=max(1, CLASSIFICATION_MAX_WORKERS)) as executor:
        futures = [executor.submit(_process_batch, idx, batch) for idx, batch in batches]
        for future in as_completed(futures):
            try:
                batch_idx, batch_labels, failed, dropped = future.result()
                results_map[batch_idx] = (batch_labels, failed, dropped)
            except Exception as exc:
                print(f"⚠️ classifier: unexpected worker error: {exc}", file=sys.stderr)

    pending_labels: list[str] = []
    total_failed = 0
    total_deadline_dropped = 0
    for i in range(0, len(pending_titles), CLASSIFICATION_BATCH_SIZE):
        batch_size = min(CLASSIFICATION_BATCH_SIZE, len(pending_titles) - i)
        batch_labels, failed, dropped = results_map.get(
            i, ([_FALLBACK_TOPIC] * batch_size, batch_size, 0)
        )
        pending_labels.extend(batch_labels)
        total_failed += failed
        total_deadline_dropped += dropped

    # ── Pass 3: write LLM labels back + populate the channel cache ──
    for i, label in zip(pending_indices, pending_labels):
        labels[i] = label
        if channels:
            ch = channels[i]
            if ch and ch != "Unknown" and ch not in channel_cache:
                if channel_counts.get(ch, 0) >= _CACHE_MIN_OCCURRENCES and label != _FALLBACK_TOPIC:
                    channel_cache[ch] = label

    # ── Pass 4: back-fill cached labels for remaining slots ──
    cache_hits = 0
    if channels:
        for i, (label, ch) in enumerate(zip(labels, channels)):
            if label is None and ch in channel_cache:
                labels[i] = channel_cache[ch]
                cache_hits += 1

    final = [l if l is not None else _FALLBACK_TOPIC for l in labels]
    return ClassificationResult(
        labels=final,
        failed=total_failed,
        deadline_dropped=total_deadline_dropped,
        cache_hits=cache_hits,
        elapsed_seconds=round(time.time() - start_time, 2),
    )


def _classify_batch_with_retry(client: OllamaClient, titles: list[str]) -> tuple[list[str], int]:
    """Returns (labels, failed_count). failed_count is len(titles) only if
    every retry attempt failed to produce a usable classification —
    a partially short-but-parseable response is padded, not retried.
    """
    prompt = build_topic_classification_prompt(titles)

    for attempt in range(CLASSIFICATION_MAX_RETRIES + 1):
        try:
            raw_response = client.generate(prompt, timeout=90)
            parsed = _extract_json(raw_response)

            if "classifications" not in parsed:
                raise ValueError("model output had no usable classifications")

            labels = parsed["classifications"]
            valid_labels = [
                lbl if lbl in TOPIC_CATEGORIES else _FALLBACK_TOPIC
                for lbl in labels
            ]
            if len(valid_labels) < len(titles):
                valid_labels.extend([_FALLBACK_TOPIC] * (len(titles) - len(valid_labels)))

            return valid_labels[: len(titles)], 0

        except (OllamaError, ValueError, Exception) as exc:
            if attempt < CLASSIFICATION_MAX_RETRIES:
                time.sleep(CLASSIFICATION_RETRY_BACKOFF_SECONDS * (attempt + 1))
            else:
                print(f"⚠️ classifier: batch failed after {CLASSIFICATION_MAX_RETRIES} retries: {exc}", file=sys.stderr)

    return [_FALLBACK_TOPIC] * len(titles), len(titles)


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