from __future__ import annotations

import zipfile
import tempfile
from pathlib import Path

from app.models import FilteredDataset
from app.ingestion.youtube_parser import YoutubeParser
from app.scoring.adapters import watch_items_to_scoring_input
from app.scoring.aggregator import aggregate_scores

SUPPORTED_SUBSCRIPTION_EXTENSIONS = (".xls", ".xlsx", ".csv", ".tsv")


class Dispatcher:

    def __init__(self):
        # holds dataset between phase 1 and phase 2
        self._cached_dataset: FilteredDataset | None = None

    # ------------------------------------------------------------------ #
    #  Phase 1 — parse only, return stats immediately                      #
    # ------------------------------------------------------------------ #

    def parse(self, path: str) -> dict:
        """
        Phase 1: reads and filters files, caches dataset, returns basic stats.
        Called when user uploads the ZIP.
        """
        p = Path(path)

        if not p.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if p.suffix.lower() == ".zip":
            dataset = self._handle_zip(p)
        elif p.is_dir():
            dataset = self._handle_folder(p)
        else:
            raise ValueError(f"Unsupported file type: {p.suffix}")

        # cache for phase 2
        self._cached_dataset = dataset

        # return only stats — no AI yet
        unsubscribed = [v for v in dataset.watched_items if not v.is_subscribed]
        subscribed   = [v for v in dataset.watched_items if v.is_subscribed]
        shorts       = [v for v in dataset.watched_items if v.is_short]

        return {
            "success": True,
            "stats": {
                "total_watched":        dataset.total_watched,
                "subscribed_count":     len(subscribed),
                "unsubscribed_count":   len(unsubscribed),
                "shorts_count":         len(shorts),
                "unique_channels":      len({v.channel_url for v in dataset.watched_items}),
                "subscribed_channels":  len(dataset.subscribed_channels),
                "analysis_period_days": dataset.analysis_period_days,
            }
        }

    # ------------------------------------------------------------------ #
    #  Phase 2 — AI analysis on cached dataset                             #
    # ------------------------------------------------------------------ #

    def analyze(self, sample_size: int = 300) -> dict:
        """
        Phase 2: runs AI on cached dataset.
        Called when user clicks 'Start Analysis'.
        """
        if self._cached_dataset is None:
            raise RuntimeError("No dataset cached. Run parse() first.")

        # sample_size is kept for API compatibility; scoring pipeline uses
        # its own smart sampling strategy internally.
        scoring_input = watch_items_to_scoring_input(self._cached_dataset)
        report = aggregate_scores(scoring_input)

        return {
            "success": True,
            "report": report
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _handle_zip(self, zip_path: Path) -> FilteredDataset:
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)
            return self._handle_folder(Path(tmpdir))

    def _handle_folder(self, root: Path) -> FilteredDataset:
        watch_path = self._find_watch_history(root)
        subs_path  = self._find_subscriptions(root)

        if not watch_path:
            raise FileNotFoundError("Watch history file not found")

        parser = YoutubeParser(
            watch_history_path=str(watch_path),
            subscriptions_path=str(subs_path) if subs_path else None,
        )
        return parser.build_dataset()

    def _find_watch_history(self, root: Path) -> Path | None:
        for f in root.rglob("*.json"):
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    sample = fp.read(500)
                if "titleUrl" in sample:
                    return f
            except Exception:
                continue
        return None

    def _find_subscriptions(self, root: Path) -> Path | None:
        for ext in SUPPORTED_SUBSCRIPTION_EXTENSIONS:
            for f in root.rglob(f"*{ext}"):
                try:
                    with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                        sample = fp.read(300)
                    if "UC" in sample and "youtube.com/channel" in sample:
                        return f
                except Exception:
                    continue
        return None

    def _get_stratified_sample(self, videos: list, n: int) -> tuple[list, dict]:
        import random

        videos = sorted(videos, key=lambda v: v.timestamp)
        n = min(n, len(videos))
        num_parts = max(1, min(n // 100, 10))
        part_size = len(videos) // num_parts
        per_part  = n // num_parts

        sample = []
        for i in range(num_parts):
            start = i * part_size
            end   = start + part_size if i < num_parts - 1 else len(videos)
            part  = videos[start:end]
            take  = min(per_part, len(part))
            sample += random.sample(part, take)

        metadata = {
            "requested":              n,
            "actual":                 len(sample),
            "total_available":        len(videos),
            "parts_used":             num_parts,
            "estimated_minutes":      round(len(sample) / 50 * 0.4, 1),
            "margin_of_error":        round(1 / (len(sample) ** 0.5) * 100, 1),
        }

        return sample, metadata