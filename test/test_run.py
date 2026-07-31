"""Manual end-to-end smoke test: parse a real Takeout export and run
the full scoring pipeline against it, printing the final report.

Not an automated test (see tests/ for those) — this exercises the
real Ollama server, so it needs `ollama serve` running locally with
the configured model pulled.

Usage:
    python test_run.py /path/to/takeout/folder-or-zip
    # or set TAKEOUT_PATH in the environment / .env file
"""

import os
import sys
import urllib.request

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from app.ingestion.dispatcher import Dispatcher
from app.scoring.adapters import watch_items_to_scoring_input
from app.scoring.aggregator import aggregate_scores

SAMPLE_SIZE = 50  # keep the manual smoke test fast


def check_ollama() -> bool:
    """Quick reachability check — purely informational, doesn't block the run."""
    try:
        urllib.request.urlopen("http://localhost:11434/", timeout=2)
        print("✅ Ollama شغال واستجاب بنجاح!")
        return True
    except Exception:
        print("⚠️ تنبيه: Ollama غير شغال أو لا يستجيب على http://localhost:11434!")
        print("👉 تأكد من فتح التيرمينال وتشغيل: ollama serve\n")
        return False


def _resolve_path() -> str:
    raw = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TAKEOUT_PATH")
    if not raw:
        print("Usage: python test_run.py /path/to/takeout/folder-or-zip")
        print("       (or set the TAKEOUT_PATH environment variable)")
        sys.exit(2)
    return raw


def main():
    print("🚀 بدء اختبار أداء OpenTrace (Optimized Run)...\n")
    check_ollama()

    takeout_path = _resolve_path()

    print("⏳ [1/4] جاري قراءة الملفات عبر الـ Dispatcher...")
    dispatcher = Dispatcher()
    result = dispatcher.parse(takeout_path)
    if not result.get("success"):
        print(f"❌ فشلت القراءة: {result.get('message')}")
        sys.exit(1)

    dataset = dispatcher._cached_dataset
    total_watched = len(dataset.watched_items)
    print(f"✅ تم العثور على {total_watched} فيديو في سجل المشاهدة.")

    if total_watched > SAMPLE_SIZE:
        print(f"⚡ [2/4] تسريع العملية: اقتطاع أول {SAMPLE_SIZE} عناصر فقط للاختبار...")
        dataset.watched_items = dataset.watched_items[:SAMPLE_SIZE]
    else:
        print("⏳ [2/4] جاري تجهيز البيانات...")

    print("⏳ [3/4] تحويل البيانات عبر الـ Adapter...")
    scoring_input = watch_items_to_scoring_input(dataset)
    print("✅ تم التحويل بنجاح!")

    print("⏳ [4/4] إرسال البيانات للـ Scoring Engine (Ollama)...")
    print("   (قد تستغرق هذه الخطوة عدة دقائق حسب سرعة الـ CPU/GPU لديك)")

    report = aggregate_scores(scoring_input)

    print("\n" + "=" * 50)
    print("🎉 تم التحليل بنجاح! التقرير النهائي:")
    print("=" * 50)
    print(report)


if __name__ == "__main__":
    main()