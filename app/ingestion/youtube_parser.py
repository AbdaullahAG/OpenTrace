from __future__ import annotations

import csv
import xlrd
import ijson
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta
from typing import List

from app.models import WatchItem, SubscribedChannel, FilteredDataset
from app.config import get_settings

settings = get_settings()


def _normalize_url(url: str) -> str:
    """Normalize URL to avoid http vs https mismatch"""
    return url.replace("https://", "http://").rstrip("/")


class YoutubeParser:
    def __init__(
        self,
        watch_history_path: str,
        subscriptions_path: str = None,
    ):
        self.watch_history_path = watch_history_path
        self.subscriptions_path = subscriptions_path
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=settings.analysis_days)

    # ------------------------------------------------------------------ #
    #  Subscriptions — supports XLS and CSV automatically                  #
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
        """Read XLS file regardless of header language"""
        try:
            workbook = xlrd.open_workbook(str(path))
            sheet    = workbook.sheet_by_index(0)
            subs     = []

            for row_idx in range(1, sheet.nrows):   # skip header
                row = sheet.row_values(row_idx)
                if len(row) < 3:
                    continue

                channel_id    = str(row[0]).strip()
                channel_url   = str(row[1]).strip()
                channel_title = str(row[2]).strip()

                if not channel_id:
                    continue

                subs.append(
                    SubscribedChannel(
                        channel_id=channel_id,
                        channel_url=channel_url,
                        channel_title=channel_title,
                    )
                )
            return subs

        except Exception:
            return []

    def _parse_csv(self, path: Path) -> List[SubscribedChannel]:
        """Fallback: read CSV or TSV"""
        subs = []
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=",")
                next(reader, None)  # skip header

                for row in reader:
                    if len(row) < 3 or not row[0].strip():
                        continue
                    subs.append(
                        SubscribedChannel(
                            channel_id=row[0].strip(),
                            channel_url=row[1].strip(),
                            channel_title=row[2].strip(),
                        )
                    )
        except Exception as e:
            print(f"[subscriptions] Error reading CSV: {e}")
        return subs

    # ------------------------------------------------------------------ #
    #  Watch History                                                        #
    # ------------------------------------------------------------------ #

    def parse_watch_history(self, subscribed_urls: set) -> List[WatchItem]:
        watched = []
        try:
            with open(self.watch_history_path, "rb") as f:
                for item in ijson.items(f, "item"):
                    # 1. التأكد أن العنصر ليس None أو فارغ
                    if not item or not isinstance(item, dict):
                        continue

                    # 2. جلب رابط الفيديو بأمان
                    title_url = item.get("titleUrl") or ""

                    # regular videos only
                    if "watch?v=" not in title_url:
                        continue

                    # extract video_id
                    parsed   = urlparse(title_url)
                    v_params = parse_qs(parsed.query) or {}
                    v_list   = v_params.get("v") or [""]
                    video_id = v_list[0] if v_list else ""
                    
                    if not video_id:
                        continue

                    # parse and filter timestamp
                    time_str = item.get("time") or ""
                    try:
                        timestamp = datetime.fromisoformat(
                            time_str.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        continue

                    if timestamp < self.cutoff:
                        continue

                    # 3. جلب بيانات القناة بأمان تامة لتفادي خطأ NoneType
                    subtitles = item.get("subtitles") or []
                    channel_name = "Unknown"
                    channel_url  = ""

                    if isinstance(subtitles, list) and len(subtitles) > 0:
                        first_sub = subtitles[0] if isinstance(subtitles[0], dict) else {}
                        channel_name = first_sub.get("name") or "Unknown"
                        channel_url  = first_sub.get("url") or ""

                    # clean title — remove locale-specific prefixes
                    raw_title = (item.get("title") or "").strip()
                    raw_title = raw_title.removeprefix("Watched ")
                    raw_title = raw_title.removeprefix("تمت مشاهدة ")

                    # skip entries with no real title
                    if len(raw_title) < 5:
                        continue

                    # detect Shorts from URL or title hashtags
                    title_lower = raw_title.lower()
                    is_short = (
                        "/shorts/" in title_url
                        or "#shorts" in title_lower
                        or "#short"  in title_lower
                        or (raw_title.endswith(".") and "#" in raw_title)
                    )

                    # cross-reference with subscriptions
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
    #  Build Final Dataset                                                  #
    # ------------------------------------------------------------------ #

    def build_dataset(self) -> FilteredDataset:
        subs = self.parse_subscriptions()

        sub_urls = {
            _normalize_url(sub.channel_url) for sub in subs if sub.channel_url
        }

        watched = self.parse_watch_history(sub_urls)

        if watched:
            oldest      = min(w.timestamp for w in watched)
            newest      = max(w.timestamp for w in watched)
            period_days = max((newest - oldest).days, 1)
        else:
            period_days = 0

        return FilteredDataset(
            watched_items=watched,
            subscribed_channels=subs,
            search_history=[],          # no search history in Takeout
            analysis_period_days=period_days,
            total_watched=len(watched),
        )