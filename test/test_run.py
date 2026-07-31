import sys
import os
import urllib.request

# 1. ضمان قراءة مسار مشروع OpenTrace وتعيين الترميز UTF-8
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from app.ingestion.dispatcher import Dispatcher
from app.scoring.adapters import watch_items_to_scoring_input
from app.scoring.aggregator import aggregate_scores

# 🔍 فحص سريع لوجود خدمة Ollama في الخلفية
def check_ollama():
    try:
        urllib.request.urlopen("http://localhost:11434/", timeout=2)
        print("✅ Ollama شغال واستجاب بنجاح!")
        return True
    except Exception:
        print("⚠️ تنبيه: Ollama غير شغال أو لا يستجيب على http://localhost:11434!")
        print("👉 تأكد من فتح التيرمينال وتشغيل: ollama serve\n")
        return False

def main():
    print("🚀 بدء اختبار أداء OpenTrace (Optimized Run)...\n")
    
    # التأكد من حالة Ollama
    check_ollama()

    # المسار الخاص بمجلد Takeout
    takeout_folder_path = r"c:\Users\DELL\Downloads\Takeout"

    # Step 1: Dispatcher
    print("⏳ [1/4] جاري قراءة الملفات من المجلد عبر הـ Dispatcher...")
    dataset = Dispatcher().run(takeout_folder_path)
    
    total_watched = len(dataset.watched_items) if hasattr(dataset, 'watched_items') else 0
    print(f"✅ تم العثور على {total_watched} فيديو في سجل المشاهدة.")

    # Step 2: Optimization (Slice Data for Fast Testing)
    # نحدد أول 10 فيديوهات فقط لتسريع التقييم بواسطة Mistral
    SAMPLE_SIZE = 50
    if total_watched > SAMPLE_SIZE:
        print(f"⚡ [2/4] تسريع العملية: اقتطاع أول {SAMPLE_SIZE} عناصر فقط للاختبار...")
        dataset.watched_items = dataset.watched_items[:SAMPLE_SIZE]
    else:
        print("⏳ [2/4] جاري تجهيز البيانات...")

    # Step 3: Adapter
    print("⏳ [3/4] تحويل البيانات عبر הـ Adapter...")
    scoring_input = watch_items_to_scoring_input(dataset)
    print("✅ تم التحويل بنجاح!")

    # Step 4: Scoring Engine
    print(f"⏳ [4/4] إرسال البيانات للـ Scoring Engine (Ollama / Mistral)...")
    print("   (قد تستغرق هذه الخطوة من 10 إلى 30 ثانية حسب سرعة الـ GPU/CPU لديك)")
    
    report = aggregate_scores(scoring_input)

    print("\n" + "="*50)
    print("🎉 تم التحليل بنجاح! التقرير النهائي:")
    print("="*50)
    print(report)

if __name__ == "__main__":
    main()