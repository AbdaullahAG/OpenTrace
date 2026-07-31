"""Tests for Dispatcher._safe_extract — zip-slip / zip-bomb protection.

Run with:
    python -m pytest tests/test_dispatcher_zip_safety.py -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.dispatcher import Dispatcher


class SafeExtractTests(unittest.TestCase):
    def _make_zip(self, entries: dict[str, bytes]) -> Path:
        tmp = Path(tempfile.mkdtemp())
        zip_path = tmp / "archive.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for name, content in entries.items():
                zf.writestr(name, content)
        return zip_path

    def test_normal_archive_extracts_fine(self):
        zip_path = self._make_zip({"watch-history.json": b'{"titleUrl": "x"}'})
        dest = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(zip_path, "r") as zf:
            Dispatcher._safe_extract(zf, dest)
        self.assertTrue((dest / "watch-history.json").exists())

    def test_zip_slip_path_traversal_is_rejected(self):
        zip_path = self._make_zip({"../../evil.txt": b"pwned"})
        dest = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(zip_path, "r") as zf:
            with self.assertRaises(ValueError):
                Dispatcher._safe_extract(zf, dest)
        # Nothing should have leaked outside dest.
        self.assertFalse((dest.parent.parent / "evil.txt").exists())

    def test_absolute_path_entry_is_rejected(self):
        zip_path = self._make_zip({"/etc/evil.txt": b"pwned"})
        dest = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(zip_path, "r") as zf:
            with self.assertRaises(ValueError):
                Dispatcher._safe_extract(zf, dest)

    def test_oversized_single_entry_is_rejected(self):
        zip_path = self._make_zip({"big.json": b"x" * 1024})
        dest = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(zip_path, "r") as zf:
            import app.ingestion.dispatcher as dispatcher_module
            original = dispatcher_module._MAX_UNCOMPRESSED_FILE_BYTES
            dispatcher_module._MAX_UNCOMPRESSED_FILE_BYTES = 100
            try:
                with self.assertRaises(ValueError):
                    Dispatcher._safe_extract(zf, dest)
            finally:
                dispatcher_module._MAX_UNCOMPRESSED_FILE_BYTES = original


if __name__ == "__main__":
    unittest.main()