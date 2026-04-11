"""
Tests for the Simulatte Persona Generator Orchestration Layer.

These are unit tests that mock the underlying pipeline functions.
They verify the orchestration logic (tier advice, cost estimation,
result structure) without making real API calls.

Run with:
    pytest tests/test_orchestrator.py -v
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario
from src.orchestrator.cost_estimator import CostEstimator
from src.orchestrator.result import CostActual, PersonaGenerationResult, QualityReport
from src.orchestrator.tier_advisor import TierAdvisor


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_brief() -> PersonaGenerationBrief:
    return PersonaGenerationBrief(
        client="TestClient",
        domain="cpg",
        business_problem="Test question",
        count=5,
        auto_confirm=True,
    )


@pytest.fixture
def deliver_brief() -> PersonaGenerationBrief:
    return PersonaGenerationBrief(
        client="LittleJoys",
        domain="cpg",
        business_problem="Why do Mumbai parents switch nutrition brands?",
        count=20,
        run_intent=RunIntent.DELIVER,
        sarvam_enabled=True,
        anchor_overrides={"location": "Mumbai"},
        simulation=SimulationScenario(
            stimuli=["Ad copy", "Product detail", "Testimonial"],
            decision_scenario="Would you buy this today?",
        ),
        auto_confirm=True,
    )


MINIMAL_COHORT_ENVELOPE = {
    "cohort_id": "test-cohort-001",
    "generated_at": "2026-04-11T00:00:00Z",
    "domain": "cpg",
    "client": "TestClient",
    "business_problem": "Test question",
    "mode": "deep",
    "icp_spec_hash": "abc123",
    "taxonomy_used": {
        "base_attributes": 100,
        "domain_extension_attributes": 20,
        "total_attributes": 120,
        "domain_data_used": False,
        "business_problem": "Test question",
        "icp_spec_hash": "abc123",
    },
    "personas": [
        {
            "persona_id": "pg-001",
            "generated_at": "2026-04-11T00:00:00Z",
            "generator_version": "2.1.0",
            "domain": "cpg",
            "mode": "deep",
            "demographic_anchor": {
                "name": "Priya Sharma",
                "age": 34,
                "gender": "female",
                "location": "Mumbai",
                "household": "family with children",
                "life_stage": "parent",
                "education": "graduate",
                "employment": "full-time",
            },
            "life_stories": [],
            "attributes": {"nutrition": {"brand_trust": {"value": 0.7, "type": "continuous", "label": "Brand Trust", "source": "inferred"}}},
            "derived_insights": {"decision_style": "analytical", "trust_anchor": "authority", "risk_appetite": "low", "consistency_score": 78},
            "behavioural_tendencies": {"price_sensitivity": {"band": "medium"}, "switching_propensity": {"band": "low"}, "objection_profile": [], "reasoning_prompt": "Priya evaluates by asking pediatricians"},
            "narrative": {"first_person": "I am a working mother...", "third_person": "She is a working mother...", "display_name": "Priya Sharma"},
            "decision_bullets": ["Trusts pediatrician recommendations"],
            "memory": {
                "core": {
                    "identity_statement": "I am a working mother of two",
                    "key_values": ["children's health", "value for money"],
                    "life_defining_events": [],
                    "relationship_map": {"primary_decision_partner": "husband", "key_influencers": [], "trust_network": []},
                    "immutable_constraints": {"budget_ceiling": None, "non_negotiables": [], "absolute_avoidances": []},
                    "tendency_summary": "Analytical decision maker",
                },
                "working": {
                    "observations": [],
                    "reflections": [],
                    "plans": [],
                    "brand_memories": {},
                    "simulation_state": {"current_turn": 0, "importance_accumulator": 0.0, "reflection_count": 0},
                },
            },
        }
    ],
    "cohort_summary": {
        "decision_style_distribution": {"analytical": 1.0},
        "trust_anchor_distribution": {"authority": 1.0},
        "risk_appetite_distribution": {"low": 1.0},
        "consistency_scores": [78],
        "distinctiveness_score": 0.45,
        "coverage_assessment": "adequate",
        "dominant_tensions": [],
    },
    "grounding_summary": {
        "tendency_source_distribution": {},
        "domain_data_signals_extracted": 0,
        "clusters_derived": 0,
    },
    "calibration_state": {
        "status": "uncalibrated",
        "method_applied": None,
        "last_calibrated": None,
        "benchmark_source": None,
        "notes": "",
    },
}


# ── TierAdvisor tests ─────────────────────────────────────────────────────────

class TestTierAdvisor:

    def test_deliver_maps_to_deep(self, deliver_brief):
        advice = TierAdvisor.advise(deliver_brief)
        assert advice.tier == "deep"
        assert "deliver" in advice.reason

    def test_explore_maps_to_signal(self, minimal_brief):
        advice = TierAdvisor.advise(minimal_brief)
        assert advice.tier == "signal"

    def test_override_respected(self):
        brief = PersonaGenerationBrief(
            client="A", domain="cpg", business_problem="Q",
            run_intent=RunIntent.DELIVER,
            tier_override="volume",
            auto_confirm=True,
        )
        advice = TierAdvisor.advise(brief)
        assert advice.tier == "volume"
        assert advice.forced is True

    def test_large_cohort_nudges_volume(self):
        brief = PersonaGenerationBrief(
            client="A", domain="cpg", business_problem="Q",
            count=300,
            run_intent=RunIntent.CALIBRATE,
            auto_confirm=True,
        )
        advice = TierAdvisor.advise(brief)
        assert advice.tier == "volume"

    def test_alt_tier_present_for_deep(self, deliver_brief):
        advice = TierAdvisor.advise(deliver_brief)
        assert advice.alt_tier == "signal"
        assert advice.alt_saving_pct is not None and advice.alt_saving_pct > 0

    def test_volume_has_no_alt_tier(self):
        brief = PersonaGenerationBrief(
            client="A", domain="cpg", business_problem="Q",
            run_intent=RunIntent.VOLUME,
            auto_confirm=True,
        )
        advice = TierAdvisor.advise(brief)
        assert advice.alt_tier is None


# ── CostEstimator tests ───────────────────────────────────────────────────────

class TestCostEstimator:

    def test_generation_cost_positive(self):
        est = CostEstimator(count=10, tier="deep")
        result = est.compute()
        assert result.gen_total > 0

    def test_sim_cost_zero_when_no_stimuli(self):
        est = CostEstimator(count=10, tier="deep", n_stimuli=0)
        result = est.compute()
        assert result.sim_total == 0.0

    def test_deep_more_expensive_than_signal(self):
        deep_est  = CostEstimator(count=10, tier="deep",   n_stimuli=5, has_decision_scenario=True)
        sig_est   = CostEstimator(count=10, tier="signal", n_stimuli=5, has_decision_scenario=True)
        vol_est   = CostEstimator(count=10, tier="volume", n_stimuli=5, has_decision_scenario=True)
        assert deep_est.compute().total > sig_est.compute().total
        assert sig_est.compute().total  > vol_est.compute().total

    def test_corpus_adds_pre_gen_cost(self):
        with_corpus    = CostEstimator(count=10, tier="signal", has_corpus=True)
        without_corpus = CostEstimator(count=10, tier="signal", has_corpus=False)
        assert with_corpus.compute().pre_gen_total > without_corpus.compute().pre_gen_total

    def test_per_persona_cost_reasonable(self):
        est = CostEstimator(count=50, tier="deep", n_stimuli=5, has_decision_scenario=True)
        result = est.compute()
        # All-in per persona should be in range $0.10–$0.35
        assert 0.10 < result.per_persona < 0.35

    def test_formatted_estimate_contains_key_strings(self):
        est = CostEstimator(count=10, tier="deep")
        output = est.formatted_estimate(brief_label="Test/cpg")
        assert "COST ESTIMATE" in output
        assert "TOTAL ESTIMATE" in output
        assert "Test/cpg" in output

    def test_time_estimate_positive(self):
        est = CostEstimator(count=10, tier="deep")
        result = est.compute()
        assert result.est_seconds_min > 0
        assert result.est_seconds_max >= result.est_seconds_min


# ── PersonaGenerationBrief validation ────────────────────────────────────────

class TestPersonaGenerationBrief:

    def test_minimal_brief_valid(self, minimal_brief):
        assert minimal_brief.client == "TestClient"
        assert minimal_brief.count == 5
        assert minimal_brief.run_intent == RunIntent.EXPLORE

    def test_tier_override_validation(self):
        with pytest.raises(Exception):
            PersonaGenerationBrief(
                client="A", domain="cpg", business_problem="Q",
                tier_override="invalid_tier",
            )

    def test_count_bounds(self):
        with pytest.raises(Exception):
            PersonaGenerationBrief(
                client="A", domain="cpg", business_problem="Q",
                count=0,
            )
        with pytest.raises(Exception):
            PersonaGenerationBrief(
                client="A", domain="cpg", business_problem="Q",
                count=501,
            )

    def test_simulation_scenario_optional(self, minimal_brief):
        assert minimal_brief.simulation is None

    def test_simulation_scenario_set(self, deliver_brief):
        assert deliver_brief.simulation is not None
        assert len(deliver_brief.simulation.stimuli) == 3


# ── PersonaGenerationResult ───────────────────────────────────────────────────

class TestPersonaGenerationResult:

    def _make_result(self) -> PersonaGenerationResult:
        return PersonaGenerationResult(
            run_id="pg-test-001",
            cohort_id="cohort-001",
            client="TestClient",
            domain="cpg",
            tier_used="signal",
            count_requested=5,
            count_delivered=5,
            cost_actual=CostActual(pre_generation=0.30, generation=0.58, simulation=0.26),
            quality_report=QualityReport(
                gates_passed=["G1", "G6", "G7"],
                gates_failed=[],
                distinctiveness_score=0.45,
                grounding_state="ungrounded",
            ),
            personas=[{"persona_id": f"pg-00{i}"} for i in range(1, 6)],
            cohort_envelope={"cohort_id": "cohort-001", "personas": []},
        )

    def test_summary_contains_key_info(self):
        r = self._make_result()
        assert "TestClient" in r.summary
        assert "SIGNAL" in r.summary
        assert "$" in r.summary

    def test_all_passed_true_when_no_failures(self):
        r = self._make_result()
        assert r.quality_report.all_passed is True

    def test_to_dict_serialisable(self):
        import json
        r = self._make_result()
        d = r.to_dict()
        json.dumps(d, default=str)  # should not raise

    def test_persona_ids(self):
        r = self._make_result()
        ids = r.persona_ids()
        assert len(ids) == 5
        assert "pg-001" in ids

    def test_get_persona_by_id(self):
        r = self._make_result()
        p = r.get_persona("pg-001")
        assert p is not None
        assert p["persona_id"] == "pg-001"

    def test_save_writes_json(self, tmp_path):
        r = self._make_result()
        out = tmp_path / "test_result.json"
        r.save(out)
        assert out.exists()
        import json
        loaded = json.loads(out.read_text())
        assert loaded["run_id"] == "pg-test-001"


# ── invoke_persona_generator (mocked) ────────────────────────────────────────

class TestInvokeOrchestrator:

    @pytest.mark.asyncio
    async def test_invoke_returns_result(self, minimal_brief, tmp_path):
        minimal_brief.output_dir = tmp_path

        with patch("src.orchestrator.invoke._run_generation", new_callable=AsyncMock) as mock_gen, \
             patch("src.orchestrator.invoke._run_simulation", new_callable=AsyncMock) as mock_sim:

            mock_gen.return_value = MINIMAL_COHORT_ENVELOPE
            mock_sim.return_value = {"simulation_id": "sim-001", "results": []}

            from src.orchestrator.invoke import invoke_persona_generator
            result = await invoke_persona_generator(minimal_brief)

        assert isinstance(result, PersonaGenerationResult)
        assert result.count_delivered == 1  # one persona in fixture
        assert result.tier_used in ("deep", "signal", "volume")
        assert result.cost_actual.total > 0
        assert result.cohort_file_path is not None

    @pytest.mark.asyncio
    async def test_invoke_creates_pipeline_doc(self, deliver_brief, tmp_path):
        deliver_brief.output_dir = tmp_path

        with patch("src.orchestrator.invoke._run_generation", new_callable=AsyncMock) as mock_gen, \
             patch("src.orchestrator.invoke._run_simulation", new_callable=AsyncMock) as mock_sim:

            mock_gen.return_value = MINIMAL_COHORT_ENVELOPE
            mock_sim.return_value = {"simulation_id": "sim-002", "results": []}

            from src.orchestrator.invoke import invoke_persona_generator
            result = await invoke_persona_generator(deliver_brief)

        assert result.pipeline_doc_path is not None
        doc = Path(result.pipeline_doc_path)
        assert doc.exists()
        content = doc.read_text()
        assert "LittleJoys" in content

    @pytest.mark.asyncio
    async def test_invoke_cancels_on_no_confirm(self, tmp_path):
        brief = PersonaGenerationBrief(
            client="A", domain="cpg", business_problem="Q",
            count=5,
            auto_confirm=False,
            output_dir=tmp_path,
        )

        async def reject_confirm(_: str) -> bool:
            return False

        with patch("src.orchestrator.invoke._run_generation", new_callable=AsyncMock):
            from src.orchestrator.invoke import invoke_persona_generator
            with pytest.raises(RuntimeError, match="cancelled by user"):
                await invoke_persona_generator(brief, confirm_callback=reject_confirm)
