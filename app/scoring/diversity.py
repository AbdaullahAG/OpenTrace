"""Source diversity, measured with Shannon entropy over channel names.

Pure math, no LLM involved — same idea used in ecology to measure
species diversity, applied here to viewing sources.
"""

from __future__ import annotations

import math
from collections import Counter


def calculate_diversity(items: list[dict]) -> float:
    """Return a 0-1 score: 0 = every view is the same channel,
    1 = every view is a different channel.
    """
    channels = [item["channel"] for item in items if item.get("channel")]
    if not channels:
        return 0.0

    counts = Counter(channels)
    total = len(channels)

    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )

    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    return round(entropy / max_entropy, 3) if max_entropy else 0.0


def top_channels(items: list[dict], limit: int = 5) -> list[dict]:
    channels = [item["channel"] for item in items if item.get("channel")]
    total = len(channels) or 1
    counts = Counter(channels)

    return [
        {"name": name, "count": count, "share": round(count / total, 3)}
        for name, count in counts.most_common(limit)
    ]
