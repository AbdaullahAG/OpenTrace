"""Builds a chronologically sorted, chart-ready timeline.

Malformed or missing timestamps are dropped rather than crashing the
whole report — one bad row from an export file shouldn't take down
the analysis.
"""

from __future__ import annotations

from collections import Counter

from dateutil import parser as date_parser


def build_timeline(items: list[dict]) -> list[dict]:
    """Return items sorted by time, each tagged with a day bucket
    (YYYY-MM-DD) so the frontend can group them into a daily chart.
    """
    dated_items = []
    for item in items:
        timestamp = item.get("timestamp")
        if not timestamp:
            continue
        try:
            parsed = date_parser.isoparse(timestamp)
        except (ValueError, TypeError):
            continue
        dated_items.append((parsed, item))

    dated_items.sort(key=lambda pair: pair[0])

    return [
        {**item, "day": parsed.date().isoformat()}
        for parsed, item in dated_items
    ]


def daily_counts(timeline: list[dict]) -> dict[str, int]:
    return dict(Counter(entry["day"] for entry in timeline if entry.get("day")))
