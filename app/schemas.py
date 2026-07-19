"""Shared data contracts.

These TypedDicts describe the JSON shapes that flow between layers.
They aren't enforced at runtime (kept lightweight for the hackathon),
but they're the single source of truth other modules should follow:

  ingestion/*  -> produces list[FeedItem]
  scoring/*    -> consumes list[FeedItem], produces BubbleReport
  gui/*        -> renders BubbleReport
"""

from __future__ import annotations

from typing import TypedDict


class FeedItem(TypedDict, total=False):
    title: str
    channel: str
    timestamp: str  # ISO 8601, e.g. "2024-01-15T10:30:00Z"
    source: str      # "youtube" | "tiktok"
    topic: str        # filled in by the scoring layer, not by ingestion


class BubbleReport(TypedDict):
    bubble_score: int              # 0-100, higher = stronger filter bubble
    diversity_score: float         # 0-1, higher = more diverse sources
    concentration_score: float     # 0-1, higher = more concentrated topics
    topic_distribution: dict[str, int]
    top_channels: list[dict]
    manipulation_flags: list[str]
    timeline: list[dict]
    ai_available: bool             # False if Ollama was unreachable
    metadata: dict
