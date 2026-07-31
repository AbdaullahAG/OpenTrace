"""Domain constants shared across the llm and scoring layers.

Kept separate from config.py: config.py holds environment-dependent
settings (.env-driven), this file holds fixed values tied to the
scoring model itself.
"""

from __future__ import annotations

TOPIC_CATEGORIES: tuple[str, ...] = (
    "music",
    "gaming",
    "technology",
    "news_politics",
    "education",
    "entertainment",
    "sports",
    "religion",
    "lifestyle_vlogs",
    "podcasts_interviews",
    "comedy",
    "other",
)

# Weights must sum to 1.0 — used by aggregator.py to compute the final score.
SCORE_WEIGHTS: dict[str, float] = {
    "diversity": 0.30,
    "concentration": 0.25,
    "algorithmic_exposure": 0.30,
    "manipulation": 0.15,
}

# Defensive limits — protect the LLM call and the app from oversized input.
MAX_ITEMS_PER_REQUEST = 5000
MAX_TITLE_LENGTH = 300
CLASSIFICATION_BATCH_SIZE = 8  # short enough for slower CPU-only inference, big enough to keep call count sane

# ── Classification throughput / reliability tuning ──────────────────────
#
# Root cause of the old "everything ends up as 'other'" bug: with
# BATCH_SIZE=5 a 250-item sample needs 50 *sequential* requests. On
# CPU-only inference (see sampler.py's own estimate: ~80 minutes for
# 300 requests) that blew straight through the old 240-second hard
# deadline, so most of the sample silently fell back to "other" with
# no retry and no visibility into what happened.
#
# Fix has three parts, applied together in classifier.py:
#   1. Run batches concurrently (CLASSIFICATION_MAX_WORKERS) instead of
#      one at a time — the dominant cost is model inference latency,
#      not CPU, so a handful of in-flight requests substantially raises
#      throughput even against a single Ollama instance.
#   2. Retry a failed/unparseable batch (CLASSIFICATION_MAX_RETRIES)
#      before giving up on it — most failures are transient (a
#      malformed JSON response, a slow model warm-up), not permanent.
#   3. Raise the overall deadline to something a real classification
#      run can plausibly finish inside, instead of ~15 batches worth.
CLASSIFICATION_MAX_WORKERS = 4          # concurrent in-flight requests to Ollama
CLASSIFICATION_MAX_RETRIES = 2          # retries per batch before falling back to "other"
CLASSIFICATION_RETRY_BACKOFF_SECONDS = 1.5
CLASSIFICATION_DEADLINE_SECONDS = 900.0  # 15 min hard ceiling for the whole classification pass

# Smart sampling — if more videos exist than this threshold, we draw a
# stratified time-based sample of SMART_SAMPLE_SIZE instead of classifying
# every video. Statistically, 400 uniformly distributed samples gives
# bubble_score estimates accurate to ±5% (95% CI).
SMART_SAMPLE_THRESHOLD = 250   # min items before sampling kicks in
SMART_SAMPLE_SIZE     = 250   # target sample size