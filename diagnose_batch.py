"""تشخيص الدفعة الحقيقية — يحاكي بالضبط batch_size=10 بعناوين حقيقية
من نتيجتك (بعضها اتصنف صح، بعضها طلع "other") عشان نعرف هل المشكلة
بحجم الدفعة، بتعقيد النص العربي، أو بشي تاني.

شغّله:
    python diagnose_batch.py
"""

import sys
sys.path.insert(0, ".")

from app.llm.ollama_client import OllamaClient
from app.llm.prompts import build_topic_classification_prompt
from app.llm.classifier import _extract_json

# نفس أول 10 عناوين بالضبط من التشغيل الحقيقي تبعك —
# بعضها طلع صح (Yanni -> music) وبعضها طلع "other" رغم وضوحه
real_batch = [
    'Kung Fu Fighting',
    'Yanni - "For All Seasons"_1080p From the Master! "Yanni Live! The Concert Event"',
    'Nathan Evans - Wellerman (Sea Shanty)',
    'Rocky III - Eye Of The Tiger',
    'In The End [Official HD Music Video] - Linkin Park',
    'Yanni - "Playtime"_1080p From the Master! "Yanni Live! The Concert Event"',
    'Kung Fu Panda 4 - Baby One More Time (Universal Pictures) HD',
    'سـورة المائدة | ٤١ - ٨١ | لفضيلة الشيخ د. ماهر المعيقلي | تراويح ليلة ٨ رمضان ١٤٤٦هـ',
    'تلاوة بديعة من سورتي النور و الفرقان للشيخ د.\u2067 #ماهر_المعيقلي\u2069 | تهجد ليلة 22 رمضان 1446هـ',
    'الشيخ الحصري - سورة الفرقان (مرتّل)',
]

client = OllamaClient()
print(f"الموديل: {client.model} | عدد العناوين: {len(real_batch)}\n")

if not client.ping():
    print("❌ Ollama مش شغّال")
    sys.exit(1)

prompt = build_topic_classification_prompt(real_batch)
raw_response = client.generate(prompt)

print("=" * 60)
print("رد Mistral الخام لنفس الدفعة الحقيقية (10 عناصر):")
print("=" * 60)
print(raw_response)
print("=" * 60)

parsed = _extract_json(raw_response)
print("\nبعد الـ parsing:")
print(parsed)

labels = parsed.get("classifications", [])
print(f"\nعدد التصنيفات المستلمة: {len(labels)} (المتوقع: {len(real_batch)})")

print("\nمقارنة كل عنوان مع تصنيفه:")
for i, title in enumerate(real_batch):
    label = labels[i] if i < len(labels) else "❌ مفقود"
    print(f"  [{label}] {title[:60]}")
