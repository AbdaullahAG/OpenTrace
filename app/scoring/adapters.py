"""Bridges ingestion's typed dataclasses to the plain-dict shape the
scoring layer expects.

Kept as a separate, tiny module rather than changing either side:
ingestion gets to keep its richer WatchItem model, scoring stays
decoupled from ingestion's internal types.
"""

from __future__ import annotations

from app.models import FilteredDataset


def watch_items_to_scoring_input(dataset: FilteredDataset) -> list[dict]:
    """Convert a FilteredDataset into the list[dict] aggregate_scores() expects.

    Extra fields (video_id, is_short, is_subscribed) ride along unused
    for now — aggregator.py ignores keys it doesn't need, so nothing
    breaks. is_subscribed in particular is worth wiring into the bubble
    signal later: content watched from channels you never subscribed to
    is exactly what "the algorithm fed you" rather than what you chose.
    """
    return [
        {
            "title": item.title,
            "channel": item.channel_name,
            "timestamp": item.timestamp.isoformat(),
            "video_id": item.video_id,
            "is_short": item.is_short,
            "is_subscribed": item.is_subscribed,
        }
        for item in dataset.watched_items
    ]
