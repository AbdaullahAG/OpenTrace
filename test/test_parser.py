import sys
import json
from pathlib import Path

TAKEOUT_PATH = r"C:\Users\ONE BY ONE\Downloads\takeout-20260720T223745Z-1-001.zip"

from app.ingestion.dispatcher import Dispatcher


def main():
    print("=" * 50)
    print("اختبار OpenTrace Parser")
    print("=" * 50)

    path = Path(TAKEOUT_PATH)
    if not path.exists():
        print(f"[خطأ] المسار غير موجود: {TAKEOUT_PATH}")
        sys.exit(1)

    print(f"\nالمسار: {TAKEOUT_PATH}")
    print("جاري التحليل...\n")

    try:
        dataset = Dispatcher().run(TAKEOUT_PATH)
    except FileNotFoundError as e:
        print(f"[خطأ] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[خطأ غير متوقع] {e}")
        raise

    subscribed     = [v for v in dataset.watched_items if v.is_subscribed]
    not_subscribed = [v for v in dataset.watched_items if not v.is_subscribed]
    shorts         = [v for v in dataset.watched_items if v.is_short]

    print("✅ تم التحليل بنجاح\n")
    print(f"📺 إجمالي المشاهدات           : {dataset.total_watched}")
    print(f"📅 الفترة الزمنية              : {dataset.analysis_period_days} يوم")
    print(f"🔔 عدد الاشتراكات             : {len(dataset.subscribed_channels)}")
    print(f"✅ من قنوات مشترك بها         : {len(subscribed)}")
    print(f"❓ مصدر غير معروف (مرشح للAI) : {len(not_subscribed)}")
    print(f"⚡ Shorts                      : {len(shorts)}")
    print()

    if not_subscribed:
        print("─" * 50)
        print("عينة من الفيديوهات المرشحة للتحليل (أول 5):")
        print("─" * 50)
        for v in not_subscribed[:5]:
            print(f"  • {v.title[:60]}")
            print(f"    القناة  : {v.channel_name}")
            print(f"    Shorts  : {'نعم' if v.is_short else 'لا'}")
            print(f"    التوقيت : {v.timestamp.strftime('%Y-%m-%d')}")
            print()

    if dataset.subscribed_channels:
        print("─" * 50)
        print("عينة من الاشتراكات (أول 5):")
        print("─" * 50)
        for ch in dataset.subscribed_channels[:5]:
            print(f"  • {ch.channel_title}")

    # ------------------------------------------------------------------ #
    #  تصدير الداتا كاملة                                                  #
    # ------------------------------------------------------------------ #
    output = {
        "total_watched": dataset.total_watched,
        "analysis_period_days": dataset.analysis_period_days,
        "subscribed_channels_count": len(dataset.subscribed_channels),
        "watched_items": [
            {
                "video_id": v.video_id,
                "title": v.title,
                "channel_name": v.channel_name,
                "channel_url": v.channel_url,
                "timestamp": v.timestamp.isoformat(),
                "is_short": v.is_short,
                "is_subscribed": v.is_subscribed,
            }
            for v in dataset.watched_items
        ],
        "subscribed_channels": [
            {
                "channel_id": ch.channel_id,
                "channel_title": ch.channel_title,
                "channel_url": ch.channel_url,
            }
            for ch in dataset.subscribed_channels
        ],
    }

    with open("dataset_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n📁 تم تصدير الداتا: dataset_output.json")


if __name__ == "__main__":
    main()