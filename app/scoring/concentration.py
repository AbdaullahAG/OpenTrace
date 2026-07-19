"""Topic concentration: how much of the content sits in one bucket.

Expects items already carry a "topic" field (added upstream by
aggregator.py via the classifier). Keeping this file LLM-free means
it stays fast, deterministic, and unit-testable without Ollama running.
"""

from __future__ import annotations

import math
from collections import Counter


def calculate_concentration(items: list[dict]) -> float:
    """Return a 0-1 score: 0 = topics evenly spread, 1 = one topic
    dominates everything.
    """
    topics = [item["topic"] for item in items if item.get("topic")]
    if not topics:
        return 0.0

    counts = Counter(topics)
    total = len(topics)

    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    diversity = entropy / max_entropy if max_entropy else 0.0

    return round(1 - diversity, 3)


def topic_distribution(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["topic"] for item in items if item.get("topic")))
