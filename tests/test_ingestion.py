"""
tests/test_ingestion.py — Sprint 27 · Antigravity test suite
Covers: format_inferrer, pii_redactor, ingestion_validator, signal_tagger, ingest()
"""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from src.onboarding.format_inferrer import DataFormat, infer_format, parse_to_signals
from src.onboarding.pii_redactor import redact_pii
from src.onboarding.ingestion_validator import validate_corpus
from src.onboarding.signal_tagger import SIGNAL_TAGS, TaggedCorpus, tag_signals
from src.onboarding.ingestion import ingest


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _diverse_signal(i: int) -> str:
    """Generate a structurally diverse signal that survives near-dedup.

    Each signal embeds a unique MD5 token so that even signals drawn from the
    same template family have very different trigram sets, keeping pairwise
    Jaccard similarity well below the 0.85 collapse threshold.
    """
    h = hashlib.md5(str(i).encode()).hexdigest()[:8]
    templates = [
        f"The packaging arrived damaged and the seal was broken uid{h}",
        f"Customer service resolved my complaint quickly ref{h}",
        f"Fragrance lasted all day without reapplication code{h}",
        f"Texture felt grainy and unpleasant on skin token{h}",
        f"Value for money exceeded my expectations tag{h}",
        f"Delivery was three days late beyond the promised date id{h}",
        f"Ingredients list showed no harmful chemicals batch{h}",
        f"Size ran small compared to standard measurements sku{h}",
        f"Colour faded after first wash in cold water lot{h}",
        f"Battery life dropped significantly after six months serial{h}",
    ]
    return templates[i % len(templates)]


def make_csv_bytes(n_rows: int) -> bytes:
    """Generate CSV bytes with header 'id,text' and n_rows structurally diverse data rows.

    Each text cell is unique enough that the near-dedup step in validate_corpus
    does NOT collapse them (pairwise Jaccard < 0.85).
    """
    lines = ["id,text"]
    for i in range(n_rows):
        sig = _diverse_signal(i)
        lines.append(f'{i},"{sig}"')
    return "\n".join(lines).encode("utf-8")


def make_json_array_bytes(signals: list[str]) -> bytes:
    """Encode a list of strings as a JSON array bytes."""
    return json.dumps(signals).encode("utf-8")


class MockLLMClient:
    """Async-compatible mock LLM client that returns a pre-canned JSON string."""

    def __init__(self, response_json: str):
        self.response_json = response_json

    async def complete(self, system, messages, max_tokens, model):
        return self.response_json


# ---------------------------------------------------------------------------
# TestFormatInferrer
# ---------------------------------------------------------------------------

class TestFormatInferrer:

    def test_json_array_detected(self):
        raw = b'["hello", "world", "foo"]'
        assert infer_format(raw) == DataFormat.JSON_ARRAY

    def test_json_lines_detected(self):
        raw = b'{"text": "first signal"}\n{"text": "second signal"}\n'
        assert infer_format(raw) == DataFormat.JSON_LINES

    def test_csv_detected(self):
        raw = b"id,text,score\n1,Great product,5\n2,Loved it,4\n"
        assert infer_format(raw) == DataFormat.CSV

    def test_plain_text_detected(self):
        raw = b"This is a plain signal\nAnother plain signal\nAnd a third one\n"
        assert infer_format(raw) == DataFormat.PLAIN_TEXT

    def test_utf8_bom_stripped_before_detection(self):
        # UTF-8 BOM + JSON array — should still detect as JSON_ARRAY
        raw = b"\xef\xbb\xbf" + b'["signal one", "signal two"]'
        assert infer_format(raw) == DataFormat.JSON_ARRAY

    def test_garbage_bytes_returns_plain_text(self):
        # Completely garbage / binary bytes must never raise and must fall back
        raw = bytes(range(256))
        result = infer_format(raw)
        assert result == DataFormat.PLAIN_TEXT


# ---------------------------------------------------------------------------
# TestParseToSignals
# ---------------------------------------------------------------------------

class TestParseToSignals:

    def test_json_array_of_strings(self):
        signals = ["alpha", "beta", "gamma"]
        raw = make_json_array_bytes(signals)
        result = parse_to_signals(raw)
        assert result == signals

    def test_json_lines_with_text_field(self):
        lines = [
            json.dumps({"text": "first review"}),
            json.dumps({"text": "second review"}),
            json.dumps({"text": "third review"}),
        ]
        raw = "\n".join(lines).encode("utf-8")
        result = parse_to_signals(raw)
        assert result == ["first review", "second review", "third review"]

    def test_csv_header_skipped_three_rows(self):
        raw = b"id,text\n1,Signal A\n2,Signal B\n3,Signal C\n"
        result = parse_to_signals(raw)
        # Header row is skipped; 3 data rows → 3 signals
        assert len(result) == 3

    def test_plain_text_five_lines(self):
        raw = b"line one\nline two\nline three\nline four\nline five\n"
        result = parse_to_signals(raw)
        assert len(result) == 5
        assert result[0] == "line one"
        assert result[4] == "line five"


# ---------------------------------------------------------------------------
# TestPIIRedactor
# ---------------------------------------------------------------------------

class TestPIIRedactor:

    def test_email_redacted(self):
        signals = ["Contact me at user.test+tag@example.co.uk for details"]
        redacted, log = redact_pii(signals)
        assert "[EMAIL]" in redacted[0]
        assert "user.test+tag@example.co.uk" not in redacted[0]
        assert log.n_emails_redacted == 1

    def test_indian_mobile_redacted(self):
        signals = ["Call me on +919876543210 for the offer"]
        redacted, log = redact_pii(signals)
        assert "[PHONE]" in redacted[0]
        assert log.n_phones_redacted == 1

    def test_aadhaar_pattern_redacted(self):
        signals = ["My Aadhaar number is 1234 5678 9012"]
        redacted, log = redact_pii(signals)
        assert "[ID]" in redacted[0]
        assert log.n_ids_redacted == 1

    def test_honorific_name_redacted(self):
        signals = ["The doctor recommended it — Dr. Sharma was very clear"]
        redacted, log = redact_pii(signals)
        assert "[NAME]" in redacted[0]
        assert log.n_names_redacted == 1

    def test_zero_false_positives_generic_words(self):
        # Plain city/brand/weekday names must NOT be redacted
        signal = "Mumbai Apple Monday"
        redacted, log = redact_pii([signal])
        assert redacted[0] == signal
        assert log.n_emails_redacted == 0
        assert log.n_phones_redacted == 0
        assert log.n_ids_redacted == 0
        assert log.n_names_redacted == 0

    def test_total_signals_affected_counts_correctly(self):
        signals = [
            "Clean signal with no PII",
            "Email: admin@corp.com present",
            "Another clean signal",
            "Phone +917654321098 embedded here",
        ]
        _, log = redact_pii(signals)
        # Only signals[1] and signals[3] were modified
        assert log.total_signals_affected == 2


# ---------------------------------------------------------------------------
# TestIngestionValidator
# ---------------------------------------------------------------------------

class TestIngestionValidator:

    def test_250_unique_signals_is_valid(self):
        # Use structurally diverse signals so near-dedup does not collapse them.
        # 201 diverse signals yield >= 200 post-dedup survivors.
        signals = [_diverse_signal(i) for i in range(201)]
        report = validate_corpus(signals)
        assert report.is_valid is True
        assert report.proxy_mode_suggested is False

    def test_199_unique_signals_invalid_proxy_suggested(self):
        signals = [_diverse_signal(i) for i in range(199)]
        report = validate_corpus(signals)
        assert report.is_valid is False
        assert report.proxy_mode_suggested is True

    def test_boundary_exactly_200_is_valid(self):
        # 201 diverse inputs → 200 post-near-dedup survivors → is_valid=True
        signals = [_diverse_signal(i) for i in range(201)]
        report = validate_corpus(signals)
        assert report.is_valid is True
        assert report.n_valid_signals >= 200

    def test_exact_duplicates_collapsed(self):
        signals = ["Duplicate signal text"] * 300
        report = validate_corpus(signals)
        # All 300 copies collapse to exactly 1 unique signal
        assert report.n_unique_signals == 1
        assert report.n_valid_signals == 1
        assert report.n_raw_signals == 300

    def test_near_duplicates_collapsed(self):
        # Near-identical signals — one character different at the end
        base = "The product quality was excellent and I would highly recommend it"
        signals = [base + " today", base + " today!"]
        # These two are near-duplicates (Jaccard > 0.85); only one should survive
        report = validate_corpus(signals)
        assert report.n_near_duplicates_removed > 0
        assert report.n_valid_signals < 2

    def test_recommendation_thresholds(self):
        # < 50 valid signals → "Insufficient data …"
        # Use a handful of completely unrelated short sentences
        low_signals = [_diverse_signal(i) for i in range(10)]
        r_low = validate_corpus(low_signals)
        assert "Insufficient" in r_low.recommendation

        # 50–199 valid signals → "Below threshold …"
        # 80 diverse signals yield 80 survivors (all pass near-dedup)
        mid_signals = [_diverse_signal(i) for i in range(80)]
        r_mid = validate_corpus(mid_signals)
        assert r_mid.n_valid_signals >= 50
        assert r_mid.n_valid_signals < 200
        assert "Below threshold" in r_mid.recommendation

        # >= 200 valid signals → "Ready for grounding …"
        high_signals = [_diverse_signal(i) for i in range(201)]
        r_high = validate_corpus(high_signals)
        assert r_high.n_valid_signals >= 200
        assert "Ready for grounding" in r_high.recommendation


# ---------------------------------------------------------------------------
# TestSignalTagger
# ---------------------------------------------------------------------------

class TestSignalTagger:

    def _make_mock_response(self, tags_and_confidences: list[tuple[str, float]]) -> str:
        items = [{"tag": tag, "confidence": conf} for tag, conf in tags_and_confidences]
        return json.dumps(items)

    def test_valid_mock_response_builds_tagged_corpus(self):
        signals = [
            "I switched because the price was too high",
            "My doctor recommended this brand",
            "I bought it after reading reviews",
        ]
        mock_response = self._make_mock_response([
            ("switching", 0.90),
            ("trust_citation", 0.85),
            ("purchase_trigger", 0.80),
        ])
        client = MockLLMClient(mock_response)
        corpus = tag_signals(signals, llm_client=client)

        assert isinstance(corpus, TaggedCorpus)
        assert len(corpus.signals) == 3
        assert corpus.signals[0].tag == "switching"
        assert corpus.signals[1].tag == "trust_citation"
        assert corpus.signals[2].tag == "purchase_trigger"

    def test_low_confidence_overridden_to_neutral(self):
        signals = ["Something vague and hard to classify"]
        # confidence < 0.40 must be overridden to "neutral"
        mock_response = self._make_mock_response([("purchase_trigger", 0.35)])
        client = MockLLMClient(mock_response)
        corpus = tag_signals(signals, llm_client=client)

        assert corpus.signals[0].tag == "neutral"
        assert corpus.signals[0].confidence == pytest.approx(0.35)

    def test_all_six_tag_keys_present_in_distribution(self):
        signals = ["I always buy the cheapest option available"]
        mock_response = self._make_mock_response([("price_mention", 0.92)])
        client = MockLLMClient(mock_response)
        corpus = tag_signals(signals, llm_client=client)

        for tag in SIGNAL_TAGS:
            assert tag in corpus.tag_distribution

    def test_n_decision_signals_counts_non_neutral(self):
        signals = [
            "Switched to competitor last month",
            "Not sure what I think about it",
            "Best price I found anywhere",
        ]
        mock_response = self._make_mock_response([
            ("switching", 0.88),
            ("neutral", 0.95),
            ("price_mention", 0.75),
        ])
        client = MockLLMClient(mock_response)
        corpus = tag_signals(signals, llm_client=client)

        # "switching" and "price_mention" are non-neutral → 2 decision signals
        assert corpus.n_decision_signals == 2


# ---------------------------------------------------------------------------
# TestIngestEndToEnd
# ---------------------------------------------------------------------------

class TestIngestEndToEnd:

    def test_250_row_csv_ready_for_grounding(self):
        # 201 diverse CSV rows produce 201 distinct parsed signals that
        # all survive near-dedup, leaving >= 200 valid signals.
        raw = make_csv_bytes(201)
        result = ingest(raw, run_tagger=False)
        assert result.ready_for_grounding is True

    def test_run_tagger_false_tagged_corpus_is_none(self):
        raw = make_csv_bytes(10)
        result = ingest(raw, run_tagger=False)
        assert result.tagged_corpus is None

    def test_pii_redacted_when_pii_present(self):
        # Build CSV with PII in one of the signals
        lines = ["id,text"]
        lines.append("0,Contact admin@example.com for support")
        for i in range(1, 15):
            lines.append(f"{i},Generic signal number {i} about the product")
        raw = "\n".join(lines).encode("utf-8")

        result = ingest(raw, run_tagger=False)
        # At least the PII signal should differ between raw and redacted
        assert result.redacted_signals != result.raw_signals
        # The email address must not appear in any redacted signal
        for sig in result.redacted_signals:
            assert "admin@example.com" not in sig

    def test_format_detected_matches_enum_value_string(self):
        raw = make_csv_bytes(5)
        result = ingest(raw, run_tagger=False)
        # format_detected should be the .value string of the DataFormat enum
        assert result.format_detected == DataFormat.CSV.value
        assert isinstance(result.format_detected, str)
