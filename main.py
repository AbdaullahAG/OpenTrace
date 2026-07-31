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

    def run_analysis(self, path: str):
        """Executes the analysis pipeline on a Takeout folder or ZIP.
        
        Returns the BubbleReport dict (see app/schemas.py) serialized 
        as JSON-safe data.
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