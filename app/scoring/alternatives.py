"""Suggests open-source alternatives based on the analysis result.

Two layers, combined:
1. Problem-based — tied to manipulation_flags (the "why" from scoring).
2. Topic-based — tied to the dominant content category (the "what").

Problem-based suggestions come first since they speak directly to what
OpenTrace just found; topic-based ones round it out with something
relevant to what the person actually watches.
"""

from __future__ import annotations

import json

from app.config import ROOT_DIR

_ALTERNATIVES_PATH = ROOT_DIR / "app" / "data" / "alternatives.json"

_FLAG_REASONS = {
    "low_source_diversity": "لأن مصادرك محدودة جداً",
    "high_topic_concentration": "لأن محتواك متركّز حول موضوع واحد",
    "high_algorithmic_exposure": "لأن معظم ما تشاهده جاء من قنوات لم تشترك بها",
    "single_channel_dominance": "لأن قناة واحدة تهيمن على مشاهداتك",
}


def suggest_alternatives(report: dict, limit: int = 5) -> list[dict]:
    """Return a de-duplicated, capped list of {name, url, description, reason}."""
    data = _load_alternatives()
    seen: set[str] = set()
    suggestions: list[dict] = []

    for flag in report.get("manipulation_flags", []):
        for alt in data.get("by_flag", {}).get(flag, []):
            _add_if_new(suggestions, seen, alt, _FLAG_REASONS.get(flag, ""))

    dominant_topic = _dominant_topic(report.get("topic_distribution", {}))
    if dominant_topic:
        reason = f"بناءً على اهتمامك بمحتوى {dominant_topic}"
        for alt in data.get("by_topic", {}).get(dominant_topic, []):
            _add_if_new(suggestions, seen, alt, reason)

    if not suggestions:
        for alt in data.get("default", []):
            _add_if_new(suggestions, seen, alt, "بديل مفتوح المصدر عام")

    return suggestions[:limit]


def _dominant_topic(topic_distribution: dict[str, int]) -> str | None:
    """Returns the most common *meaningful* topic — "other" is skipped
    since it isn't an actionable category (mirrors app.js's headline logic,
    so the "content dominance" message and the alternative suggestions
    always agree on what the dominant topic actually is).
    """
    ranked = sorted(topic_distribution.items(), key=lambda pair: -pair[1])
    for topic, count in ranked:
        if topic != "other" and count > 0:
            return topic
    return None


def _add_if_new(suggestions: list[dict], seen: set[str], alt: dict, reason: str) -> None:
    if alt["name"] in seen:
        return
    seen.add(alt["name"])
    suggestions.append({**alt, "reason": reason})


def _load_alternatives() -> dict:
    try:
        with open(_ALTERNATIVES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
