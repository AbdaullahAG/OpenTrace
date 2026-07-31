from __future__ import annotations

import zipfile
import tempfile
from pathlib import Path

from app.models import FilteredDataset
from app.ingestion.youtube_parser import YoutubeParser
from app.scoring.adapters import watch_items_to_scoring_input
from app.scoring.aggregator import aggregate_scores

SUPPORTED_SUBSCRIPTION_EXTENSIONS = (".xls", ".xlsx", ".csv", ".tsv")

# ── Zip-extraction safety limits ────────────────────────────────────────
#
# The input here is a Google Takeout export the user selects themselves,
# but treating it as trusted just because it's "the user's own file" is
# exactly the assumption that bites you if the file was tampered with,
# downloaded from somewhere else, or simply corrupted. `zipfile.extractall`
# has no built-in protection against:
#   - Zip Slip: an entry named e.g. "../../../etc/cron.d/x" that resolves
#     outside the extraction directory when naively joined.
#   - Zip bombs: a tiny archive that decompresses to gigabytes, exhausting
#     disk/RAM.
# Both are validated before a single byte is extracted.
_MAX_UNCOMPRESSED_TOTAL_BYTES = 2 * 1024 * 1024 * 1024   # 2 GB — generous for a Takeout export
_MAX_UNCOMPRESSED_FILE_BYTES = 512 * 1024 * 1024          # 512 MB per single file
_MAX_COMPRESSION_RATIO = 100                              # flag suspiciously extreme compression


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
                self._safe_extract(zf, Path(tmpdir))
            return self._handle_folder(Path(tmpdir))

    @staticmethod
    def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
        """Validate every entry before extracting (zip-slip / zip-bomb guard).

        Raises ``ValueError`` — caught by ``main.py``'s ``API.parse`` and
        reported back to the UI as a normal, user-facing error — rather
        than letting a crafted archive write outside ``dest`` or exhaust
        disk space silently.
        """
        dest = dest.resolve()
        total_uncompressed = 0

        for info in zf.infolist():
            # Zip Slip: resolve the target path and make sure it's still
            # inside `dest`. Path.resolve() collapses "..", so a member
            # like "../../evil" would resolve outside `dest` and be caught.
            target = (dest / info.filename).resolve()
            if target != dest and dest not in target.parents:
                raise ValueError(f"Unsafe path in archive, refusing to extract: {info.filename}")

            if info.is_dir():
                continue

            if info.file_size > _MAX_UNCOMPRESSED_FILE_BYTES:
                raise ValueError(
                    f"Archive entry too large ({info.file_size} bytes): {info.filename}"
                )

            # Guard against zip bombs: absurd compression ratios on a
            # non-trivial file are a classic red flag.
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > _MAX_COMPRESSION_RATIO and info.file_size > 1024 * 1024:
                    raise ValueError(
                        f"Archive entry has a suspicious compression ratio: {info.filename}"
                    )

            total_uncompressed += info.file_size
            if total_uncompressed > _MAX_UNCOMPRESSED_TOTAL_BYTES:
                raise ValueError("Archive is too large once decompressed — refusing to extract.")

        zf.extractall(dest)

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