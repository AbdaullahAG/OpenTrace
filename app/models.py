from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WatchItem:
    video_id: str
    title: str
    channel_name: str
    channel_url: str
    timestamp: datetime
    is_short: bool
    is_subscribed: bool


@dataclass
class SearchItem:
    query: str
    timestamp: datetime


@dataclass
class SubscribedChannel:
    channel_id: str
    channel_url: str
    channel_title: str


@dataclass
class FilteredDataset:
    watched_items: list[WatchItem]
    subscribed_channels: list[SubscribedChannel]
    search_history: list[SearchItem]
    analysis_period_days: int
    total_watched: int