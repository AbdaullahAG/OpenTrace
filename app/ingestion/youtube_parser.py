from __future__ import annotations

import csv
import html
import re
import xlrd
import ijson
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.models import WatchItem, SubscribedChannel, FilteredDataset
from app.config import get_settings

settings = get_settings()


def _sanitize_text(text: Optional[str]) -> str:
    """OWASP A03 Input Sanitization: Clean up control characters and HTML entities."""
    if not text:
        return ""
    # Unescape HTML entities (e.g. &amp; -> &)
    cleaned = html.unescape(text.strip())
    # Remove null bytes and non-printable control characters
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    return cleaned.strip()


def _normalize_url(url: str) -> str:
    """Normalize URL to avoid http vs https mismatch."""
    if not url:
        return ""
    cleaned = url.strip()
    return cleaned.replace("https://", "http://").rstrip("/")


def _extract_channel_from_url(url: str) -> Optional[str]:
    """Fallback logic: Extract handle or channel ID from YouTube channel URL.
    Handles formats like:
    - https://www.youtube.com/@CairokeeOfficial
    - https://www.youtube.com/channel/UC123456789
    - https://www.youtube.com/c/ChannelName
    - https://www.youtube.com/user/UserName
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        
        if not path:
            return None

        parts = path.split("/")
        first_part = parts[0]

        # Handle @handle style
        if first_part.startswith("@"):
            handle = unquote(first_part[1:]).strip()
            return handle if handle else None

        # Handle /channel/UC..., /c/..., /user/...
        if len(parts) >= 2 and first_part in ("channel", "c", "user", "u"):
            extracted = unquote(parts[1]).strip()
            return extracted if extracted else None

        # Direct path fallback
        if len(parts) == 1 and not first_part.startswith("watch"):
            extracted = unquote(first_part).strip()
            return extracted if extracted else None

    except Exception:
        pass

    return None


class YoutubeParser:
    def __init__(
        self,
        watch_history_path: str,
        subscriptions_path: Optional[str] = None,
    ):
        self.watch_history_path = watch_history_path
        self.subscriptions_path = subscriptions_path
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=settings.analysis_days)

    # ------------------------------------------------------------------ #
    #  Subscriptions — supports XLS and CSV automatically                #
    # ------------------------------------------------------------------ #

    def parse_subscriptions(self) -> List[SubscribedChannel]:
        if not self.subscriptions_path:
            return []

        path = Path(self.subscriptions_path)

        result = self._parse_xls(path)
        if result:
            return result

        return self._parse_csv(path)

    def _parse_xls(self, path: Path) -> List[SubscribedChannel]:
        """Read XLS file regardless of header language."""
        try:
            workbook = xlrd.open_workbook(str(path))
            sheet = workbook.sheet_by_index(0)
            subs = []

            for row_idx in range(1, sheet.nrows):  # skip header
                row = sheet.row_values(row_idx)
                if len(row) < 3:
                    continue

                channel_id = _sanitize_text(str(row[0]))
                channel_url = _sanitize_text(str(row[1]))
                channel_title = _sanitize_text(str(row[2]))

                if not channel_id:
                    continue

                subs.append(
                    SubscribedChannel(
                        channel_id=channel_id,
                        channel_url=channel_url,
                        channel_title=channel_title or channel_id,
                    )
                )
            return subs

        except Exception:
            return []

    def _parse_csv(self, path: Path) -> List[SubscribedChannel]:
        """Fallback: read CSV or TSV."""
        subs = []
        try:
            with open(path, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f, delimiter=",")
                next(reader, None)  # skip header

                for row in reader:
                    if len(row) < 3 or not row[0].strip():
                        continue
                    subs.append(
                        SubscribedChannel(
                            channel_id=_sanitize_text(row[0]),
                            channel_url=_sanitize_text(row[1]),
                            channel_title=_sanitize_text(row[2]),
                        )
                    )
        except Exception as e:
            print(f"[subscriptions] Error reading CSV: {e}")
        return subs

    # ------------------------------------------------------------------ #
    #  Watch History                                                     #
    # ------------------------------------------------------------------ #

    def parse_watch_history(self, subscribed_urls: set) -> List[WatchItem]:
        watched = []
        try:
            with open(self.watch_history_path, "rb") as f:
                for item in ijson.items(f, "item"):
                    if not item or not isinstance(item, dict):
                        continue

                    title_url = _sanitize_text(item.get("titleUrl"))

                    # Flexible URL check: accept watch?v=, /shorts/, or /live/
                    if not any(k in title_url for k in ("watch?v=", "/shorts/", "/live/")):
                        continue

                    # Extract video_id safely
                    parsed = urlparse(title_url)
                    video_id = ""

                    if "watch?v=" in title_url:
                        v_params = parse_qs(parsed.query) or {}
                        v_list = v_params.get("v") or [""]
                        video_id = v_list[0]
                    elif "/shorts/" in title_url:
                        video_id = parsed.path.split("/shorts/")[-1].split("/")[0]
                    elif "/live/" in title_url:
                        video_id = parsed.path.split("/live/")[-1].split("/")[0]

                    if not video_id:
                        continue

                    # Parse timestamp with timezone safety
                    time_str = item.get("time") or ""
                    try:
                        timestamp = datetime.fromisoformat(
                            time_str.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        continue

                    if timestamp < self.cutoff:
                        continue

                    # Robust Channel Extraction (Eliminating "Unknown")
                    subtitles = item.get("subtitles") or []
                    channel_name = ""
                    channel_url = ""

                    if isinstance(subtitles, list) and len(subtitles) > 0:
                        first_sub = subtitles[0] if isinstance(subtitles[0], dict) else {}
                        raw_name = _sanitize_text(first_sub.get("name"))
                        channel_url = _sanitize_text(first_sub.get("url"))

                        # Reject generic "Unknown" strings
                        if raw_name and raw_name.lower() not in ("unknown", "null", "none"):
                            channel_name = raw_name

                    # Fallback 1: Extract from channel_url if name missing/unknown
                    if not channel_name and channel_url:
                        extracted_handle = _extract_channel_from_url(channel_url)
                        if extracted_handle:
                            channel_name = extracted_handle

                    # Fallback 2: Default clean name if still unresolved
                    if not channel_name:
                        channel_name = "Unknown Channel"

                    # Clean video title
                    raw_title = _sanitize_text(item.get("title"))
                    raw_title = raw_title.removeprefix("Watched ")
                    raw_title = raw_title.removeprefix("تمت مشاهدة ")

                    if len(raw_title) < 2:
                        continue

                    # Detect Shorts
                    title_lower = raw_title.lower()
                    is_short = (
                        "/shorts/" in title_url
                        or "#shorts" in title_lower
                        or "#short" in title_lower
                        or (raw_title.endswith(".") and "#" in raw_title)
                    )

                    # Subscribed match check
                    is_subscribed = _normalize_url(channel_url) in (subscribed_urls or set())

                    watched.append(
                        WatchItem(
                            video_id=video_id,
                            title=raw_title,
                            channel_name=channel_name,
                            channel_url=channel_url,
                            timestamp=timestamp,
                            is_short=is_short,
                            is_subscribed=is_subscribed,
                        )
                    )

        except FileNotFoundError:
            print("[watch_history] File not found")
        except Exception as e:
            print(f"[watch_history] Error reading file: {e}")

        return watched

    # ------------------------------------------------------------------ #
    #  Build Final Dataset                                               #
    # ------------------------------------------------------------------ #

    def build_dataset(self) -> FilteredDataset:
        subs = self.parse_subscriptions()

        sub_urls = {
            _normalize_url(sub.channel_url) for sub in subs if sub.channel_url
        }

        watched = self.parse_watch_history(sub_urls)

        if watched:
            oldest = min(w.timestamp for w in watched)
            newest = max(w.timestamp for w in watched)
            period_days = max((newest - oldest).days, 1)
        else:
            period_days = 0

        return FilteredDataset(
            watched_items=watched,
            subscribed_channels=subs,
            search_history=[],
            analysis_period_days=period_days,
            total_watched=len(watched),
        )