"""Combines every scoring signal into the single report the GUI renders.

This is the only file that talks to both the LLM layer and the pure
scoring functions — everything else stays decoupled and independently
testable.
"""

from __future__ import annotations

from app.constants import SCORE_WEIGHTS
from app.llm.classifier import classify_topics
from app.llm.ollama_client import OllamaClient, OllamaError
from app.scoring.concentration import calculate_concentration, topic_distribution
from app.scoring.diversity import calculate_diversity, top_channels
from app.scoring.exposure import algorithmic_exposure_share
from app.scoring.security import sanitize_items
from app.scoring.timeline import build_timeline

_HIGH_CONCENTRATION = 0.7
_LOW_DIVERSITY = 0.3
_DOMINANT_CHANNEL_SHARE = 0.5
_HIGH_ALGORITHMIC_EXPOSURE = 0.7


def aggregate_scores(items: list[dict], *, client: OllamaClient | None = None) -> dict:
    """Run the full pipeline: sanitize -> classify -> score -> report.

    Degrades gracefully if Ollama is unreachable: the report still
    comes back with diversity and timeline data, `ai_available: False`,
    and a concentration score of 0 rather than a crash.
    """
    clean_items = sanitize_items(items)
    if not clean_items:
        return _empty_report()

    client = client or OllamaClient()
    ai_available = client.ping()

    if ai_available:
        titles = [item["title"] for item in clean_items if item.get("title")]
        try:
            distribution = classify_topics(client, titles)
            clean_items = _attach_topics(clean_items, titles, distribution)
        except OllamaError:
            ai_available = False

    diversity_score = calculate_diversity(clean_items)
    concentration_score = calculate_concentration(clean_items) if ai_available else 0.0
    exposure_score = algorithmic_exposure_share(clean_items)

    bubble_score = round(
        100 * (
            SCORE_WEIGHTS["diversity"] * (1 - diversity_score)
            + SCORE_WEIGHTS["concentration"] * concentration_score
            + SCORE_WEIGHTS["algorithmic_exposure"] * exposure_score
            + SCORE_WEIGHTS["manipulation"] * _manipulation_weight(clean_items)
        )
    )

    return {
        "bubble_score": bubble_score,
        "diversity_score": diversity_score,
        "concentration_score": concentration_score,
        "algorithmic_exposure_score": exposure_score,
        "topic_distribution": topic_distribution(clean_items),
        "top_channels": top_channels(clean_items),
        "manipulation_flags": _manipulation_flags(diversity_score, concentration_score, exposure_score, clean_items),
        "timeline": build_timeline(clean_items),
        "ai_available": ai_available,
        "metadata": {
            "total_items": len(clean_items),
            "unique_channels": len({i["channel"] for i in clean_items if i.get("channel")}),
        },
    }


def _attach_topics(items: list[dict], titles: list[str], distribution: dict[str, int]) -> list[dict]:
    # classify_topics returns aggregate counts, not per-item labels, which
    # is all the concentration math needs — we fan the counts back out so
    # concentration.py can stay a simple per-item reader.
    expanded_topics: list[str] = []
    for topic, count in distribution.items():
        expanded_topics.extend([topic] * count)

    return [
        {**item, "topic": expanded_topics[i] if i < len(expanded_topics) else "other"}
        for i, item in enumerate(items)
    ]


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
        "metadata": {"total_items": 0, "unique_channels": 0},
    }
