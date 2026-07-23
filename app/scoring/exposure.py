"""Algorithmic exposure: how much of what you watched came from
channels you never subscribed to.

This is the most direct bubble signal available — subscribed content
is what you chose, unsubscribed content is what the algorithm surfaced.
"""

from __future__ import annotations


def algorithmic_exposure_share(items: list[dict]) -> float:
    """Return 0-1: share of items from unsubscribed channels.

    Returns 0.0 if no item carries an "is_subscribed" field — older
    data sources (e.g. a TikTok parser without subscription data)
    degrade to "no signal" rather than a false high score.
    """
    flagged = [item for item in items if "is_subscribed" in item]
    if not flagged:
        return 0.0

    unsubscribed = sum(1 for item in flagged if not item["is_subscribed"])
    return round(unsubscribed / len(flagged), 3)
