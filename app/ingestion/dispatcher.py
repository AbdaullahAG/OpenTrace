from __future__ import annotations

import zipfile
import tempfile
from pathlib import Path

from app.models import FilteredDataset
from app.ingestion.youtube_parser import YoutubeParser


SUPPORTED_SUBSCRIPTION_EXTENSIONS = (".xls", ".xlsx", ".csv", ".tsv")


class Dispatcher:

    def run(self, path: str) -> FilteredDataset:
        p = Path(path)

        if not p.exists():
            raise FileNotFoundError(f"المسار غير موجود: {path}")

        if p.suffix.lower() == ".zip":
            return self._handle_zip(p)

        if p.is_dir():
            return self._handle_folder(p)

        raise ValueError(f"نوع الملف غير مدعوم: {p.suffix}")

    def _handle_zip(self, zip_path: Path) -> FilteredDataset:
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)
            return self._handle_folder(Path(tmpdir))

    def _handle_folder(self, root: Path) -> FilteredDataset:
        watch_path = self._find_watch_history(root)
        subs_path  = self._find_subscriptions(root)

        if not watch_path:
            raise FileNotFoundError("لم يتم العثور على ملف سجل المشاهدة")

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
            matches = list(root.rglob(f"*{ext}"))
            if matches:
                return matches[0]
        return None