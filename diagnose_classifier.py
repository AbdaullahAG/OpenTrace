"""تشخيص مباشر — يوري بالضبط شو Mistral بيرد، بدون أي fallback أو معالجة.

شغّله بعد ما تحدّث الملفات (classifier.py, prompts.py, constants.py, aggregator.py):

    python diagnose_classifier.py

لو النتيجة لسه "other" لكل شي، المشكلة بالموديل نفسه مش بالكود.
لو طلعت متنوعة، يبقى المشكلة كانت الكود القديم ولازم تستبدل الملفات.
"""

import sys
sys.path.insert(0, ".")

from app.llm.ollama_client import OllamaClient
from app.llm.prompts import build_topic_classification_prompt

# عناوين واضحة عمداً — لو حتى هاي طلعت "other" فالمشكلة بالموديل مش بالبيانات
test_titles = [
    "Python Full Course for Beginners",              # المفروض: technology أو education
    "Yanni - Live Concert",                            # المفروض: music
    "سورة الفرقان - الشيخ الحصري",                        # المفروض: religion
    "Kung Fu Panda 4 - Official Trailer",             # المفروض: entertainment
    "Champions League Highlights",                     # المفروض: sports
]

client = OllamaClient()
print(f"الموديل: {client.model} | العنوان: {client.host}\n")

if not client.ping():
    print("❌ Ollama مش شغّال — شغّل 'ollama serve' وحاول تاني")
    sys.exit(1)

prompt = build_topic_classification_prompt(test_titles)
print("=" * 60)
print("الـ Prompt المرسل:")
print("=" * 60)
print(prompt)

raw_response = client.generate(prompt)
print("\n" + "=" * 60)
print("رد Mistral الخام (بدون أي معالجة):")
print("=" * 60)
print(raw_response)
print("=" * 60)
