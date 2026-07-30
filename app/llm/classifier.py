"""Orchestrates topic classification: batches titles, calls the LLM,
and safely parses whatever comes back.

Small local models don't always return clean JSON — this is the one
place that has to assume the model's output is unreliable and never
trust it blindly (no eval(), no assuming well-formed JSON).

Optimisations (v2)
------------------
Channel-level result cache
    The same channel often appears dozens of times in a watch history
    (e.g. "تلاوات د. ماهر المعيقلي" × 13).  Sending the same title
    pattern to Mistral repeatedly wastes time.  Instead, classify each
    *channel* only once and reuse the label for every subsequent video
    from that channel — without ever sending data to the network.

    Cache key  : ``channel`` field of the scoring dict (exact string).
    Cache value: topic label string.

    Videos whose channel is empty / unknown still go through the normal
    LLM path so no title is silently misclassified.
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from app.constants import CLASSIFICATION_BATCH_SIZE, TOPIC_CATEGORIES
from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompts import build_topic_classification_prompt

_FALLBACK_TOPIC = "other"
# Minimum number of times a channel must appear for us to cache its
# label — avoids caching one-off channels that won't recur anyway.
_CACHE_MIN_OCCURRENCES = 2


def classify_topics(
    client: OllamaClient,
    titles: list[str],
    *,
    channels: list[str] | None = None,
) -> list[str]:
    """Classify titles into topic categories, one label per title, in
    the same order as the input.

    Parameters
    ----------
    client:
        Live OllamaClient instance.
    titles:
        List of video titles to classify.
    channels:
        Optional parallel list of channel names (same length as titles).
        When provided, a channel cache is built: if a channel has
        appeared ``_CACHE_MIN_OCCURRENCES`` or more times its first
        classified label is reused for every later occurrence, saving
        one LLM call per duplicate.

    Never raises — on any failure (Ollama down, bad output) the
    affected titles simply get "other" so the caller can keep going
    with a degraded-but-honest result.
    """
    if channels and len(channels) != len(titles):
        # Safety: mismatched lists → ignore channels to avoid index errors
        channels = None

    channel_cache: dict[str, str] = {}
    labels: list[str | None] = [None] * len(titles)

    # ── Pass 1: serve already-cached channels without hitting the LLM ──
    if channels:
        channel_counts = Counter(
            ch for ch in channels if ch and ch != "Unknown"
        )
        # For each high-frequency channel, only the FIRST occurrence goes to
        # the LLM (pending_indices); all subsequent occurrences stay as None
        # and are back-filled in Pass 4 once the cache is populated.
        pending_indices: list[int] = []
        seen_channels: set[str] = set()  # tracks channels already queued for LLM
        for i, (title, ch) in enumerate(zip(titles, channels)):
            if ch and ch != "Unknown" and channel_counts[ch] >= _CACHE_MIN_OCCURRENCES:
                if ch in channel_cache:
                    labels[i] = channel_cache[ch]   # cache hit — no LLM needed
                elif ch in seen_channels:
                    pass                             # 2nd+ occurrence — wait for Pass 4
                else:
                    pending_indices.append(i)        # first occurrence — classify once
                    seen_channels.add(ch)
            else:
                pending_indices.append(i)  # unique / unknown channel — always classify
    else:
        pending_indices = list(range(len(titles)))

    # ── Pass 2: classify only the pending titles via the LLM ──
    pending_titles = [titles[i] for i in pending_indices]
    pending_labels: list[str] = []

    for start in range(0, len(pending_titles), CLASSIFICATION_BATCH_SIZE):
        batch = pending_titles[start : start + CLASSIFICATION_BATCH_SIZE]
        batch_labels = _classify_batch(client, batch)
        pending_labels.extend(
            label if label in TOPIC_CATEGORIES else _FALLBACK_TOPIC
            for label in batch_labels
        )

    # ── Pass 3: write LLM labels back + populate channel cache ──
    for i, label in zip(pending_indices, pending_labels):
        labels[i] = label
        if channels:
            ch = channels[i]
            if ch and ch != "Unknown" and ch not in channel_cache:
                channel_counts_val = channel_counts.get(ch, 0)  # type: ignore[union-attr]
                if channel_counts_val >= _CACHE_MIN_OCCURRENCES:
                    channel_cache[ch] = label

    # ── Pass 4: back-fill cached labels for any remaining None slots ──
    # (slots that were pending because the channel hadn't been seen yet)
    if channels:
        for i, (label, ch) in enumerate(zip(labels, channels)):
            if label is None and ch in channel_cache:
                labels[i] = channel_cache[ch]

    # Final safety: replace any remaining None with fallback
    final = [l if l is not None else _FALLBACK_TOPIC for l in labels]

    # Log cache efficiency
    cache_hits = sum(1 for l in labels if l is not None and l != _FALLBACK_TOPIC) - len(pending_indices) + len(pending_titles)
    if channel_cache:
        print(
            f"ℹ️  classifier: channel cache built ({len(channel_cache)} channels cached, "
            f"~{len(titles) - len(pending_titles)} LLM calls saved)",
            file=sys.stderr,
        )

    return final


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
