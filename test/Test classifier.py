"""Automated tests for app.llm.classifier.

These replace guesswork with real assertions: a mocked OllamaClient
stands in for the network call so the tests run instantly and
deterministically, without needing a live Ollama server.

Run with:
    python -m pytest tests/test_classifier.py -v
or (no pytest available):
    python -m unittest tests.test_classifier -v
"""

from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm import classifier
from app.llm.ollama_client import OllamaError


def _json_response(labels: list[str]) -> str:
    return json.dumps({"classifications": labels})


class FakeClient:
    """Stands in for OllamaClient.generate with scripted behavior."""

    def __init__(self, responder):
        self.responder = responder
        self.calls: list[list[str]] = []

    def generate(self, prompt, *, timeout=90, json_mode=False, max_tokens=None, temperature=0.2):
        return self.responder(prompt)


class ClassifyTopicsTests(unittest.TestCase):
    def test_all_titles_classified_in_order(self):
        titles = [f"title {i}" for i in range(20)]

        def responder(prompt):
            n_lines = len([l for l in prompt.split("Titles:")[1].split("Respond")[0].splitlines() if l.strip()])
            return _json_response(["technology"] * n_lines)

        client = FakeClient(responder)
        result = classifier.classify_topics(client, titles)

        self.assertEqual(len(result.labels), len(titles))
        self.assertTrue(all(l == "technology" for l in result.labels))
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.deadline_dropped, 0)

    def test_retries_before_falling_back(self):
        titles = ["a", "b", "c"]
        attempts = {"n": 0}

        def responder(prompt):
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise OllamaError("simulated transient failure")
            return _json_response(["music", "gaming", "news"])

        client = FakeClient(responder)
        with patch("app.llm.classifier.CLASSIFICATION_RETRY_BACKOFF_SECONDS", 0.01):
            result = classifier.classify_topics(client, titles)

        self.assertEqual(result.labels, ["music", "gaming", "news"])
        self.assertEqual(result.failed, 0)
        self.assertGreaterEqual(attempts["n"], 2)

    def test_exhausted_retries_fall_back_to_other_and_are_counted_as_failed(self):
        titles = ["a", "b"]

        def responder(prompt):
            raise OllamaError("ollama is down")

        client = FakeClient(responder)
        with patch("app.llm.classifier.CLASSIFICATION_RETRY_BACKOFF_SECONDS", 0.01):
            result = classifier.classify_topics(client, titles)

        self.assertEqual(result.labels, ["other", "other"])
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.deadline_dropped, 0)  # distinct from a deadline drop

    def test_deadline_drop_is_tracked_separately_from_failed(self):
        titles = ["a", "b"]

        def slow_responder(prompt):
            time.sleep(0.3)
            return _json_response(["music", "music"])

        client = FakeClient(slow_responder)
        with patch("app.llm.classifier.CLASSIFICATION_DEADLINE_SECONDS", 0.01):
            result = classifier.classify_topics(client, titles)

        self.assertEqual(result.labels, ["other", "other"])
        self.assertEqual(result.deadline_dropped, 2)
        self.assertEqual(result.failed, 0)  # not a model/parse failure — ran out of time

    def test_channel_cache_avoids_redundant_llm_calls(self):
        titles = ["Ep 1", "Ep 2", "Ep 3", "Unrelated video"]
        channels = ["Same Channel", "Same Channel", "Same Channel", "Other Channel"]
        call_count = {"n": 0}

        def responder(prompt):
            call_count["n"] += 1
            n_lines = len([l for l in prompt.split("Titles:")[1].split("Respond")[0].splitlines() if l.strip()])
            return _json_response(["education"] * n_lines)

        client = FakeClient(responder)
        result = classifier.classify_topics(client, titles, channels=channels)

        self.assertEqual(result.labels, ["education", "education", "education", "education"])
        # Only 1 LLM call needed: "Same Channel" (first occurrence) and
        # "Other Channel" both fit in a single batch (CLASSIFICATION_BATCH_SIZE=8);
        # the 2 repeat occurrences of "Same Channel" are served from cache.
        self.assertEqual(call_count["n"], 1)
        self.assertGreaterEqual(result.cache_hits, 2)

    def test_invalid_category_in_response_is_replaced_not_trusted(self):
        titles = ["a", "b"]

        def responder(prompt):
            return _json_response(["not_a_real_category", "music"])

        client = FakeClient(responder)
        with patch("app.llm.classifier.CLASSIFICATION_RETRY_BACKOFF_SECONDS", 0.01):
            result = classifier.classify_topics(client, titles)

        # First label is invalid -> replaced with fallback after retries exhausted,
        # second was valid and must be preserved rather than discarded wholesale.
        self.assertEqual(result.labels[1], "music")
        self.assertIn(result.labels[0], classifier.TOPIC_CATEGORIES)

    def test_malformed_json_does_not_raise(self):
        titles = ["a"]

        def responder(prompt):
            return "not json at all { broken"

        client = FakeClient(responder)
        with patch("app.llm.classifier.CLASSIFICATION_RETRY_BACKOFF_SECONDS", 0.01):
            result = classifier.classify_topics(client, titles)

        self.assertEqual(result.labels, ["other"])
        self.assertEqual(result.failed, 1)


if __name__ == "__main__":
    unittest.main()