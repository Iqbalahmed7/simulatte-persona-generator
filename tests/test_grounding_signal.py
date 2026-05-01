"""Tests for src/grounding/signal_extractor.py

Sprint 8 — Grounding Pipeline, Stage 1: Signal Extraction.
10 tests, all pure keyword-matching (no LLM, no integration flag required).
"""
import pytest


def test_price_mention_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["This product is too expensive for me."])
    types = [s.signal_type for s in signals]
    assert "price_mention" in types


def test_purchase_trigger_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["I bought this yesterday at the store."])
    types = [s.signal_type for s in signals]
    assert "purchase_trigger" in types


def test_rejection_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["I avoided buying this — too risky."])
    types = [s.signal_type for s in signals]
    assert "rejection" in types


def test_switching_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["I switched from my old brand last month."])
    types = [s.signal_type for s in signals]
    assert "switching" in types


def test_trust_citation_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["My doctor recommended this supplement."])
    types = [s.signal_type for s in signals]
    assert "trust_citation" in types


def test_multi_signal_text():
    """Text with price + trust triggers → at least 2 signals."""
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["It was expensive but my doctor recommended it."])
    assert len(signals) >= 2


def test_empty_text_skipped():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["", "  ", "I bought it."])
    assert len(signals) >= 1
    for s in signals:
        assert s.text.strip() != ""


def test_signals_to_vectors_shape():
    from src.grounding.signal_extractor import extract_signals, signals_to_vectors
    signals = extract_signals([
        "Too expensive — I avoided it.",
        "My friend recommended this brand.",
        "Switched to a cheaper option.",
    ])
    vectors = signals_to_vectors(signals)
    assert len(vectors) == len(signals)
    for v in vectors:
        assert len(v) == 9
        assert all(isinstance(x, float) for x in v)
        assert all(0.0 <= x <= 1.0 for x in v)


def test_signals_to_vectors_price_flag():
    """price_mention signal → vector[0] == 1.0."""
    from src.grounding.signal_extractor import signals_to_vectors
    from src.grounding.types import Signal
    sig = Signal(id="test-1", text="Too expensive!", signal_type="price_mention")
    vector = signals_to_vectors([sig])[0]
    assert vector[0] == 1.0


def test_unmatched_text_produces_no_signals():
    """Text with no keywords should produce no synthetic fallback signal."""
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["This is a vague comment with no specific words."])
    assert len(signals) == 0
