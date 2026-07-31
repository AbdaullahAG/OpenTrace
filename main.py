import os
import sys
import traceback

import webview

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.ingestion.dispatcher import Dispatcher


# Keep one Dispatcher instance alive for the whole app lifetime
# so phase-2 analysis can reuse the cached dataset from phase-1 parsing.
dispatcher = Dispatcher()


class API:
    """Exposed to the frontend via pywebview's js_api.

    Every method here is callable from JS as
    window.pywebview.api.<method_name>(...).
    """

    def select_takeout_path(self):
        """Opens a native file picker for .zip files OR a folder picker.

        Initiates a file dialog prioritizing .zip archives. Returns None if 
        canceled. The dispatcher handles both .zip and folder paths.

        Returns the chosen path as a string, or None on cancel.
        """
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("ZIP Archive (*.zip)", "JSON File (*.json)", "All Files (*.*)"),
        )
        if not result:
            return None
        return result[0]

    def select_takeout_folder(self):
        """Fallback: opens a native directory picker.

        Provides support for directories extracted from the Takeout zip file.
        """
        result = webview.windows[0].create_file_dialog(
            webview.FOLDER_DIALOG
        )
        if not result:
            return None
        return result[0]

    def parse(self, path: str):
        """Phase 1: parse input and cache dataset in dispatcher."""
        try:
            return dispatcher.parse(path)
        except FileNotFoundError as exc:
            return {"success": False, "message": str(exc)}
        except (ValueError, RuntimeError) as exc:
            return {"success": False, "message": str(exc)}
        except Exception as exc:
            traceback.print_exc()
            return {"success": False, "message": f"تعذّرت قراءة الملفات: {exc}"}

    def analyze(self, sample_size: int = 300):
        """Phase 2: run AI analysis over the cached dataset."""
        try:
            return dispatcher.analyze(sample_size)
        except RuntimeError as exc:
            return {"success": False, "message": str(exc)}
        except Exception as exc:
            traceback.print_exc()
            return {"success": False, "message": f"فشل التحليل: {exc}"}

    def run_analysis(self, sample_size: int = 300):
        """Backward-compatible alias used by older frontend code."""
        return self.analyze(sample_size)


def start():
    api = API()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "app", "gui", "index.html")

    webview.create_window(
        title="OpenTrace",
        url=f"file://{html_path}",
        js_api=api,
        width=1200,
        height=800,
    )
    # Devtools/debug console should only be on for local development —
    # leaving it on unconditionally exposes the DOM/JS console (and thus
    # window.pywebview.api) in a shipped build.
    webview.start(debug=get_settings().debug)


if __name__ == "__main__":
    start()