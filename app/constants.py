"""Domain constants shared across the llm and scoring layers.

Kept separate from config.py: config.py holds environment-dependent
settings (.env-driven), this file holds fixed values tied to the
scoring model itself.
"""

from __future__ import annotations

TOPIC_CATEGORIES: tuple[str, ...] = (
    "politics",
    "sports",
    "entertainment",
    "technology",
    "news",
    "education",
    "music",
    "gaming",
    "religion",
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
CLASSIFICATION_BATCH_SIZE = 5  # keeps each request short enough for slower CPU-only inference
