import os
import sys
import traceback

import webview

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ingestion.dispatcher import Dispatcher
from app.scoring.adapters import watch_items_to_scoring_input
from app.scoring.aggregator import aggregate_scores


class BackendAPI:
    """Exposed to the frontend via pywebview's js_api.

    Every method here is callable from JS as
    window.pywebview.api.<method_name>(...).
    """

    def select_takeout_path(self):
        """Opens a native folder picker and returns the chosen path.

        Returns the folder path as a string, or None if the user
        cancelled the dialog.
        """
        result = webview.windows[0].create_file_dialog(
            webview.FOLDER_DIALOG
        )
        if not result:
            return None
        return result[0]

    def run_analysis(self, path: str):
        """Runs the full pipeline on a Takeout folder or ZIP and
        returns the BubbleReport dict (see app/schemas.py) as JSON-safe
        data — pywebview serializes the return value automatically.
        """
        try:
            dataset = Dispatcher().run(path)
        except FileNotFoundError as exc:
            return {"success": False, "message": str(exc)}
        except Exception as exc:
            traceback.print_exc()
            return {"success": False, "message": f"تعذّرت قراءة الملفات: {exc}"}

        if not dataset.watched_items:
            return {
                "success": False,
                "message": "لم يتم العثور على سجل مشاهدة في هذا المسار.",
            }

        scoring_input = watch_items_to_scoring_input(dataset)

        try:
            report = aggregate_scores(scoring_input)
        except Exception as exc:
            traceback.print_exc()
            return {"success": False, "message": f"فشل التحليل: {exc}"}

        return {"success": True, "report": report}


def start():
    api = BackendAPI()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "app", "gui", "index.html")

    webview.create_window(
        title="OpenTrace",
        url=f"file://{html_path}",
        js_api=api,
        width=1200,
        height=800,
    )
    webview.start(debug=True)


if __name__ == "__main__":
    start()
