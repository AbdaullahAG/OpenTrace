"""Combines every scoring signal into the single report the GUI renders.

This is the only file that talks to both the LLM layer and the pure
scoring functions — everything else stays decoupled and independently
testable.

Performance optimisations applied here (v2)
-------------------------------------------
1. Smart sampling  (sampler.py)
   If the dataset exceeds SMART_SAMPLE_THRESHOLD, a stratified
   time-based sample of SMART_SAMPLE_SIZE items is drawn for the AI
   classification step only.  All other scoring signals (diversity,
   exposure, timeline) still use the *full* dataset so they remain
   accurate.

2. Channel result cache  (classifier.py)
   The same channel appearing many times only triggers one LLM call;
   subsequent occurrences reuse the cached label.
"""

from __future__ import annotations

import sys
from datetime import datetime

from app.constants import SCORE_WEIGHTS
from app.llm.classifier import classify_topics
from app.llm.ollama_client import OllamaClient, OllamaError
from app.scoring.alternatives import suggest_alternatives
from app.scoring.concentration import calculate_concentration, topic_distribution
from app.scoring.diversity import calculate_diversity, top_channels
from app.scoring.exposure import algorithmic_exposure_share
from app.scoring.sampler import sample_for_classification
from app.scoring.security import sanitize_items
from app.scoring.timeline import build_timeline

_HIGH_CONCENTRATION = 0.7
_LOW_DIVERSITY = 0.3
_DOMINANT_CHANNEL_SHARE = 0.5
_HIGH_ALGORITHMIC_EXPOSURE = 0.7


def aggregate_scores(items: list[dict], *, client: OllamaClient | None = None) -> dict:
    """Run the full pipeline: sanitize → (sample) → classify → score → report.

    Degrades gracefully if Ollama is unreachable: the report still
    comes back with diversity and timeline data, ``ai_available: False``,
    and a concentration score of 0 rather than a crash.
    """
    clean_items = sanitize_items(items)
    if not clean_items:
        return _empty_report()

    client = client or OllamaClient()
    ai_available = client.ping()

    # ── Smart sample for the AI step only ──────────────────────────── #
    sample_items, was_sampled = sample_for_classification(clean_items)
    if was_sampled:
        print(
            f"ℹ️  aggregator: dataset has {len(clean_items)} items — "
            f"using a stratified sample of {len(sample_items)} for AI classification.",
            file=sys.stderr,
        )

    classification_stats = None
    if ai_available:
        try:
            sample_items, classification_stats = _attach_topics(sample_items, client)
        except OllamaError:
            ai_available = False

    # ── Scoring signals ─────────────────────────────────────────────── #
    # Diversity, exposure, and timeline always use the full dataset.
    # Concentration uses the (possibly sampled) classified items.
    diversity_score    = calculate_diversity(clean_items)
    concentration_score = calculate_concentration(sample_items) if ai_available else 0.0
    exposure_score     = algorithmic_exposure_share(clean_items)

    bubble_score = round(
        100 * (
            SCORE_WEIGHTS["diversity"]             * (1 - diversity_score)
            + SCORE_WEIGHTS["concentration"]       * concentration_score
            + SCORE_WEIGHTS["algorithmic_exposure"]* exposure_score
            + SCORE_WEIGHTS["manipulation"]        * _manipulation_weight(clean_items)
        )
    )

    timestamps = []
    for item in clean_items:
        if "timestamp" in item:
            try:
                dt = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                timestamps.append(dt)
            except ValueError:
                pass
    analysis_period_days = max(1, (max(timestamps) - min(timestamps)).days) if timestamps else 0

    exposure_items = [i for i in clean_items if "is_subscribed" in i]
    exposure_total = len(exposure_items)
    exposure_unsubscribed = sum(1 for i in exposure_items if not i["is_subscribed"])

    metadata_extra = {}
    if classification_stats is not None:
        # Surfaced so the UI can tell the person "N items couldn't be
        # classified in time" instead of silently mixing them into a
        # genuine model verdict of "other".
        metadata_extra = {
            "classification_llm_calls_cached": classification_stats.cache_hits,
            "classification_deadline_dropped": classification_stats.deadline_dropped,
            "classification_failed": classification_stats.failed,
            "classification_elapsed_seconds": classification_stats.elapsed_seconds,
        }

    report = {
        "bubble_score": bubble_score,
        "diversity_score": diversity_score,
        "concentration_score": concentration_score,
        "algorithmic_exposure_score": exposure_score,
        "topic_distribution": topic_distribution(sample_items),
        "top_channels": top_channels(clean_items),
        "manipulation_flags": _manipulation_flags(diversity_score, concentration_score, exposure_score, clean_items),
        "timeline": build_timeline(clean_items),
        "ai_available": ai_available,
        "metadata": {
            "total_items": len(clean_items),
            "unique_channels": len({i["channel"] for i in clean_items if i.get("channel")}),
            "sampled_for_ai": was_sampled,
            "sample_size": len(sample_items) if was_sampled else len(clean_items),
            "analysis_period_days": analysis_period_days,
            "exposure_total": exposure_total,
            "exposure_unsubscribed": exposure_unsubscribed,
            **metadata_extra,
        },
    }
    report["suggested_alternatives"] = suggest_alternatives(report)
    return report


def _attach_topics(items: list[dict], client: OllamaClient) -> tuple[list[dict], "ClassificationResult"]:
    """Classify and attach a ``"topic"`` to each item that has a title.

    Returns the updated items alongside the full ClassificationResult
    so aggregate_scores() can surface *why* items ended up as "other"
    (genuine failure vs deadline drop vs cache hit) in the report.
    """
    titled_indices = [i for i, item in enumerate(items) if item.get("title")]
    titles   = [items[i]["title"]   for i in titled_indices]
    channels = [items[i].get("channel", "") for i in titled_indices]

    result = classify_topics(client, titles, channels=channels)

    updated = list(items)
    for index, label in zip(titled_indices, result.labels):
        updated[index] = {**updated[index], "topic": label}

    return updated, result

def _manipulation_weight(items: list[dict]) -> float:
    channels = top_channels(items, limit=1)
    return channels[0]["share"] if channels else 0.0


def _manipulation_flags(
    diversity_score: float,
    concentration_score: float,
    exposure_score: float,
    items: list[dict],
) -> list[str]:
    flags = []
    if diversity_score < _LOW_DIVERSITY:
        flags.append("low_source_diversity")
    if concentration_score > _HIGH_CONCENTRATION:
        flags.append("high_topic_concentration")
    if exposure_score > _HIGH_ALGORITHMIC_EXPOSURE:
        flags.append("high_algorithmic_exposure")

    dominant = top_channels(items, limit=1)
    if dominant and dominant[0]["share"] > _DOMINANT_CHANNEL_SHARE:
        flags.append("single_channel_dominance")

    return flags


def _empty_report() -> dict:
    return {
        "bubble_score": 0,
        "diversity_score": 0.0,
        "concentration_score": 0.0,
        "algorithmic_exposure_score": 0.0,
        "topic_distribution": {},
        "top_channels": [],
        "manipulation_flags": [],
        "timeline": [],
        "ai_available": False,
        "suggested_alternatives": [],
        "metadata": {
            "total_items": 0,
            "unique_channels": 0,
            "sampled_for_ai": False,
            "sample_size": 0,
            "analysis_period_days": 0,
            "exposure_total": 0,
            "exposure_unsubscribed": 0,
        },
    }