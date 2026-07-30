"""Smart stratified sampler for the AI classification step.

Why this matters
----------------
A user with 1 500+ videos in their history would trigger ~300 LLM
requests (at CLASSIFICATION_BATCH_SIZE=5), which can take 80+ minutes
on CPU-only hardware.  A uniformly-random sample of 400 items drawn
across the *full time span* gives bubble_score estimates accurate to
±5 % at 95 % CI — the same principle used by opinion polls.

How the stratification works
-----------------------------
1. Sort items by timestamp.
2. Divide into N equal-width time buckets (``_STRATA``).
3. From each bucket draw ``ceil(target / N)`` items at random *without
   replacement* (or all items if the bucket is smaller).

This guarantees coverage of both old and recent content — a pure random
sample on a skewed history (most activity in the last 30 days) would
under-represent older viewing patterns.

Public API
----------
sample_for_classification(items, target) -> list[dict]
    Returns a sub-list of *items* of length ≤ target, preserving the
    dict structure expected by aggregator.py.  If len(items) ≤ target
    the original list is returned unchanged (no sampling overhead).
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from app.constants import SMART_SAMPLE_SIZE, SMART_SAMPLE_THRESHOLD

_STRATA = 10  # number of time buckets — more strata = better temporal coverage


def sample_for_classification(
    items: list[dict],
    target: int = SMART_SAMPLE_SIZE,
) -> tuple[list[dict], bool]:
    """Return a representative sample and whether sampling was applied.

    Parameters
    ----------
    items:
        Full list of scoring-layer dicts (must have a ``"timestamp"`` key).
    target:
        Desired sample size.  Defaults to ``SMART_SAMPLE_SIZE``.

    Returns
    -------
    (sample, was_sampled)
        ``was_sampled`` is ``True`` only when the input exceeded the
        threshold and a sub-sample was actually drawn.
    """
    if len(items) <= SMART_SAMPLE_THRESHOLD:
        return items, False

    sample = _stratified_sample(items, target)
    return sample, True


# ------------------------------------------------------------------ #
#  Internal helpers                                                    #
# ------------------------------------------------------------------ #

def _stratified_sample(items: list[dict], target: int) -> list[dict]:
    """Stratified random sample across ``_STRATA`` equal time buckets."""
    sorted_items = _sort_by_time(items)
    n = len(sorted_items)

    bucket_size = math.ceil(n / _STRATA)
    per_bucket  = math.ceil(target / _STRATA)

    sample: list[dict] = []
    for bucket_start in range(0, n, bucket_size):
        bucket = sorted_items[bucket_start : bucket_start + bucket_size]
        k = min(per_bucket, len(bucket))
        sample.extend(random.sample(bucket, k))

    # Trim to exact target in case rounding gave us slightly more
    if len(sample) > target:
        random.shuffle(sample)
        sample = sample[:target]

    return sample


def _sort_by_time(items: Sequence[dict]) -> list[dict]:
    """Sort by the ``timestamp`` string field (ISO-8601 sorts lexicographically)."""
    return sorted(items, key=lambda x: x.get("timestamp", ""))
