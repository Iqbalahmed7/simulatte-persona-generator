"""tests/test_attribute_provenance.py

Unit tests for AttributeProvenance schema and AttributeFiller provenance emission.

Coverage:
  P1 — AttributeProvenance model validates correctly
  P2 — Attribute accepts provenance=None (backward-compat)
  P3 — Attribute accepts a full AttributeProvenance
  P4 — AttributeFiller emits provenance on LLM-filled attributes (mocked LLM)
  P5 — AttributeFiller emits empirical provenance on anchored/override attributes
  P6 — AttributeFiller fallback path emits provenance with confidence=0.1
  P7 — key_influences hallucination guard: reported attrs not in context are dropped
  P8 — generation_stage propagates correctly for anchor / extended / domain_specific
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schema.persona import Attribute, AttributeProvenance, GenerationStage


# ---------------------------------------------------------------------------
# P1 — AttributeProvenance validates
# ---------------------------------------------------------------------------

class TestAttributeProvenanceModel:
    def test_valid_empirical(self):
        p = AttributeProvenance(
            source_class="empirical",
            source_detail="demographic_anchor",
            confidence=1.0,
            conditioned_by=[],
            reasoning=None,
            generation_stage="anchor",
            filled_at=datetime.now(timezone.utc),
        )
        assert p.source_class == "empirical"
        assert p.confidence == 1.0
        assert p.conditioned_by == []
        assert p.reasoning is None

    def test_valid_inferred(self):
        p = AttributeProvenance(
            source_class="inferred",
            source_detail="llm_inference_claude-sonnet-4-6",
            confidence=0.82,
            conditioned_by=["risk_tolerance", "income_bracket"],
            reasoning="High income + low risk tolerance suggest premium-but-cautious orientation.",
            generation_stage="extended",
            filled_at=datetime.now(timezone.utc),
        )
        assert p.source_class == "inferred"
        assert len(p.conditioned_by) == 2

    def test_invalid_source_class(self):
        with pytest.raises(Exception):
            AttributeProvenance(
                source_class="unknown",  # not in Literal
                source_detail="x",
                confidence=0.5,
                conditioned_by=[],
                reasoning=None,
                generation_stage="anchor",
                filled_at=datetime.now(timezone.utc),
            )

    def test_invalid_generation_stage(self):
        with pytest.raises(Exception):
            AttributeProvenance(
                source_class="empirical",
                source_detail="x",
                confidence=0.5,
                conditioned_by=[],
                reasoning=None,
                generation_stage="batch",  # not in Literal — "batch" was removed
                filled_at=datetime.now(timezone.utc),
            )


# ---------------------------------------------------------------------------
# P2 / P3 — Attribute backward-compat and provenance field
# ---------------------------------------------------------------------------

class TestAttributeModel:
    def test_provenance_defaults_to_none(self):
        """Existing call sites that don't pass provenance must still validate."""
        attr = Attribute(value=0.7, type="continuous", label="high", source="sampled")
        assert attr.provenance is None

    def test_provenance_accepted_when_set(self):
        p = AttributeProvenance(
            source_class="inferred",
            source_detail="llm_inference_test",
            confidence=0.75,
            conditioned_by=["age"],
            reasoning="Test reasoning.",
            generation_stage="extended",
            filled_at=datetime.now(timezone.utc),
        )
        attr = Attribute(value=0.7, type="continuous", label="high", source="sampled", provenance=p)
        assert attr.provenance is not None
        assert attr.provenance.confidence == 0.75

    def test_categorical_with_provenance(self):
        p = AttributeProvenance(
            source_class="empirical",
            source_detail="demographic_anchor",
            confidence=1.0,
            conditioned_by=[],
            reasoning=None,
            generation_stage="anchor",
            filled_at=datetime.now(timezone.utc),
        )
        attr = Attribute(value="premium", type="categorical", label="premium", source="anchored", provenance=p)
        assert attr.value == "premium"
        assert attr.provenance.source_class == "empirical"


# ---------------------------------------------------------------------------
# Helpers for filler tests
# ---------------------------------------------------------------------------

def _make_attr_def(name: str = "test_attr", category: str = "psychology",
                   attr_type: str = "continuous", options=None):
    """Build a minimal AttributeDefinition-like mock."""
    d = MagicMock()
    d.name = name
    d.category = category
    d.attr_type = attr_type
    d.options = options or []
    d.description = "Test attribute description."
    d.population_prior = 0.5
    d.anchor_order = None
    return d


def _make_demographic_anchor():
    anchor = MagicMock()
    anchor.name = "TestPersona"
    anchor.age = 34
    anchor.gender = "female"
    anchor.location.urban_tier = "metro"
    anchor.household.income_bracket = "middle"
    anchor.life_stage = "established_adult"
    anchor.worldview = None
    return anchor


def _make_llm_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps(payload))]
    resp.usage = MagicMock(input_tokens=50, output_tokens=30,
                           cache_read_input_tokens=0, cache_creation_input_tokens=0)
    return resp


# ---------------------------------------------------------------------------
# P4 — LLM-filled attribute emits inferred provenance
# ---------------------------------------------------------------------------

class TestAttributeFillerProvenance:
    def _make_filler(self, response_payload: dict):
        from src.generation.attribute_filler import AttributeFiller
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=_make_llm_response(response_payload))
        return AttributeFiller(llm_client=client, model="claude-haiku-4-5")

    @pytest.mark.asyncio
    async def test_inferred_provenance_populated(self):
        filler = self._make_filler({
            "value": 0.65,
            "label": "medium",
            "confidence": 0.82,
            "reasoning": "Mid-income persona tends toward moderate brand loyalty.",
            "key_influences": ["income_bracket", "age"],
        })
        attr_def = _make_attr_def("brand_loyalty")
        profile = {"income_bracket": "middle", "age": 34}
        result = await filler._fill_single_attribute(
            attr_def, profile, _make_demographic_anchor(), generation_stage="extended"
        )
        assert result.provenance is not None
        p = result.provenance
        assert p.source_class == "inferred"
        assert "llm_inference" in p.source_detail
        assert p.confidence == 0.82
        assert p.reasoning is not None
        assert p.generation_stage == "extended"
        assert "income_bracket" in p.conditioned_by
        assert "age" in p.conditioned_by

    @pytest.mark.asyncio
    async def test_anchor_stage_propagates(self):
        filler = self._make_filler({
            "value": 0.4,
            "label": "medium",
            "confidence": 0.9,
            "reasoning": "Anchor stage fill.",
            "key_influences": [],
        })
        attr_def = _make_attr_def("risk_tolerance")
        result = await filler._fill_single_attribute(
            attr_def, {}, _make_demographic_anchor(), generation_stage="anchor"
        )
        assert result.provenance is not None
        assert result.provenance.generation_stage == "anchor"

    @pytest.mark.asyncio
    async def test_domain_specific_stage_propagates(self):
        filler = self._make_filler({
            "value": "high",
            "label": "high",
            "confidence": 0.77,
            "reasoning": "Domain-specific fill.",
            "key_influences": [],
        })
        attr_def = _make_attr_def("domain_custom", attr_type="categorical", options=["low", "medium", "high"])
        result = await filler._fill_single_attribute(
            attr_def, {}, _make_demographic_anchor(), generation_stage="domain_specific"
        )
        assert result.provenance.generation_stage == "domain_specific"


# ---------------------------------------------------------------------------
# P5 — Anchor override attributes receive empirical provenance
# ---------------------------------------------------------------------------

class TestAnchorProvenance:
    def test_anchor_attr_gets_empirical_provenance(self):
        """Direct construction of anchored Attribute (as done in fill() Step 2)."""
        from datetime import datetime, timezone
        p = AttributeProvenance(
            source_class="empirical",
            source_detail="demographic_anchor",
            confidence=1.0,
            conditioned_by=[],
            reasoning=None,
            generation_stage="anchor",
            filled_at=datetime.now(timezone.utc),
        )
        attr = Attribute(value="metro", type="categorical", label="metro",
                         source="anchored", provenance=p)
        assert attr.provenance.source_class == "empirical"
        assert attr.provenance.confidence == 1.0
        assert attr.provenance.conditioned_by == []


# ---------------------------------------------------------------------------
# P6 — Fallback path emits provenance with confidence=0.1
# ---------------------------------------------------------------------------

class TestFallbackProvenance:
    @pytest.mark.asyncio
    async def test_fallback_provenance_on_llm_failure(self):
        from src.generation.attribute_filler import AttributeFiller
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=Exception("LLM timeout"))
        filler = AttributeFiller(llm_client=client, model="claude-haiku-4-5")
        attr_def = _make_attr_def("resilience")
        result = await filler._fill_single_attribute(
            attr_def, {}, _make_demographic_anchor(), generation_stage="extended"
        )
        assert result.provenance is not None
        assert result.provenance.confidence == 0.1
        assert "fallback_prior" in result.provenance.source_detail
        assert result.provenance.reasoning is not None


# ---------------------------------------------------------------------------
# P7 — Hallucination guard: key_influences not in context are stripped
# ---------------------------------------------------------------------------

class TestHallucinationGuard:
    @pytest.mark.asyncio
    async def test_influences_not_in_context_are_dropped(self):
        from src.generation.attribute_filler import AttributeFiller
        # LLM reports an influence that wasn't in the context window
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=_make_llm_response({
            "value": 0.5,
            "label": "medium",
            "confidence": 0.6,
            "reasoning": "Some reasoning.",
            "key_influences": ["income_bracket", "HALLUCINATED_ATTR"],
        }))
        filler = AttributeFiller(llm_client=client, model="claude-haiku-4-5")
        attr_def = _make_attr_def("some_attr")
        profile = {"income_bracket": "middle"}  # HALLUCINATED_ATTR not here
        result = await filler._fill_single_attribute(
            attr_def, profile, _make_demographic_anchor()
        )
        assert "income_bracket" in result.provenance.conditioned_by
        assert "HALLUCINATED_ATTR" not in result.provenance.conditioned_by
