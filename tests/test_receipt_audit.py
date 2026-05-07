"""tests/test_receipt_audit.py — Glass-box provenance receipt audit gate (Spec 03).

Verifies that every PersonaResponse ships with a populated ResponseReceipt.
No LLM calls — decide() is stubbed with a receipt-bearing mock output.

Fails closed: if receipt is None or missing required fields, the test fails.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.schema.receipt import (
    RECEIPT_SCHEMA_VERSION,
    ArchetypeAnchor,
    ResponseReceipt,
    SignalTrace,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_receipt() -> ResponseReceipt:
    return ResponseReceipt(
        source_signals=[
            SignalTrace(
                signal_name="price_sensitivity",
                signal_category="behavioral",
                signal_value="high",
                influence_direction="against",
            )
        ],
        archetype_anchor=ArchetypeAnchor(
            decision_style="analytical",
            value_orientation="quality",
            active_tendencies=["price_sensitive_high"],
        ),
        confidence_score=72,
        confidence_flags=[],
        out_of_distribution=False,
        ood_reason=None,
        noise_applied=3,
        foundation_version=None,
    )


def _make_mock_decision_output(with_receipt: bool = True):
    from src.cognition.decide import DecisionOutput

    output = DecisionOutput(
        decision="Yes",
        confidence=72,
        reasoning_trace="step 1 → step 2 → step 3",
        gut_reaction="positive",
        key_drivers=["quality", "price"],
        objections=[],
        what_would_change_mind="",
        noise_applied=3,
        follow_up_action="",
        implied_purchase=False,
        receipt=_make_receipt() if with_receipt else None,
    )
    return output


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persona_response_carries_receipt():
    """Every PersonaResponse must have a non-None receipt after decide()."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.modalities.survey import SurveyQuestion, run_survey

    persona = make_synthetic_persona()
    questions = [SurveyQuestion(id="q1", text="Would you buy this product?")]

    mock_output = _make_mock_decision_output(with_receipt=True)

    with patch(
        "src.modalities.survey.decide",
        new=AsyncMock(return_value=mock_output),
    ):
        with patch("src.modalities.survey.reset_working_memory", side_effect=lambda p: p):
            result = await run_survey(questions=questions, personas=[persona])

    assert len(result.responses) == 1
    resp = result.responses[0]
    assert resp.receipt is not None, "PersonaResponse.receipt must not be None"


@pytest.mark.asyncio
async def test_receipt_has_required_fields():
    """Receipt must have schema_version, source_signals, and archetype_anchor."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.modalities.survey import SurveyQuestion, run_survey

    persona = make_synthetic_persona()
    questions = [SurveyQuestion(id="q1", text="Rate this brand.")]

    mock_output = _make_mock_decision_output(with_receipt=True)

    with patch(
        "src.modalities.survey.decide",
        new=AsyncMock(return_value=mock_output),
    ):
        with patch("src.modalities.survey.reset_working_memory", side_effect=lambda p: p):
            result = await run_survey(questions=questions, personas=[persona])

    receipt = result.responses[0].receipt
    assert receipt.schema_version == RECEIPT_SCHEMA_VERSION
    assert isinstance(receipt.source_signals, list)
    assert len(receipt.source_signals) > 0, "Receipt must have at least one source signal"
    assert receipt.archetype_anchor is not None
    assert receipt.archetype_anchor.decision_style
    assert receipt.archetype_anchor.value_orientation


def test_receipt_builder_produces_receipt():
    """build_receipt() returns a fully populated ResponseReceipt with no LLM calls."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cognition.receipt_builder import build_receipt

    persona = make_synthetic_persona()
    receipt = build_receipt(persona=persona, confidence=65, noise_applied=5)

    assert receipt is not None
    assert receipt.schema_version == RECEIPT_SCHEMA_VERSION
    assert len(receipt.source_signals) > 0

    categories = {s.signal_category for s in receipt.source_signals}
    assert "behavioral" in categories, "Must include behavioral signals"
    assert "psychographic" in categories, "Must include psychographic signals"
    assert "demographic" in categories, "Must include demographic signals"

    assert receipt.archetype_anchor is not None
    assert receipt.confidence_score == 65
    assert receipt.noise_applied == 5


def test_ood_flag_set_below_threshold():
    """out_of_distribution must be True when confidence < OOD_CONFIDENCE_THRESHOLD."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cognition.receipt_builder import build_receipt
    from src.schema.receipt import OOD_CONFIDENCE_THRESHOLD

    persona = make_synthetic_persona()
    low_confidence = OOD_CONFIDENCE_THRESHOLD - 1
    receipt = build_receipt(persona=persona, confidence=low_confidence, noise_applied=0)

    assert receipt.out_of_distribution is True
    assert receipt.ood_reason is not None


def test_ood_flag_clear_above_threshold():
    """out_of_distribution must be False when confidence >= OOD_CONFIDENCE_THRESHOLD."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cognition.receipt_builder import build_receipt
    from src.schema.receipt import OOD_CONFIDENCE_THRESHOLD

    persona = make_synthetic_persona()
    receipt = build_receipt(persona=persona, confidence=OOD_CONFIDENCE_THRESHOLD, noise_applied=0)

    assert receipt.out_of_distribution is False
    assert receipt.ood_reason is None
