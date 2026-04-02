"""tests/test_live_e2e.py — Live end-to-end tests against the real Anthropic API.

Tests are skipped by default. Set RUN_LIVE_TESTS=1 to enable them.

Usage:
    # Skip all live tests (default):
    python3 -m pytest tests/test_live_e2e.py -v

    # Run live tests:
    RUN_LIVE_TESTS=1 python3 -m pytest tests/test_live_e2e.py -v
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest

# ---------------------------------------------------------------------------
# Skip marker: all tests skipped unless RUN_LIVE_TESTS=1 is set
# ---------------------------------------------------------------------------

live = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="Live API tests skipped. Set RUN_LIVE_TESTS=1 to enable.",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_cohort(envelope_dict: dict, path) -> str:
    """Save a cohort envelope dict to a JSON file, return path string."""
    dest = str(path / "cohort.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(envelope_dict, f, indent=2, default=str)
    return dest


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@live
def test_live_generate_cpg_cohort(tmp_path):
    """Generate a 3-persona CPG cohort and verify the envelope structure."""
    from src.cli import _run_generation

    result = asyncio.run(
        _run_generation(
            count=3,
            domain="cpg",
            mode="quick",
            anchor_overrides={},
            persona_id_prefix="live",
            domain_data=None,
            sarvam_enabled=False,
            skip_gates=True,
        )
    )

    assert isinstance(result, dict), "Result must be a dict"
    assert "personas" in result, f"Expected 'personas' key, got: {list(result.keys())}"
    assert len(result["personas"]) == 3, (
        f"Expected 3 personas, got {len(result['personas'])}"
    )

    for persona in result["personas"]:
        assert "persona_id" in persona, f"Persona missing 'persona_id': {persona.keys()}"
        assert "demographic_anchor" in persona, f"Persona missing 'demographic_anchor'"
        assert "attributes" in persona, f"Persona missing 'attributes'"


@live
def test_live_generate_saas_cohort(tmp_path):
    """Generate a 3-persona SaaS cohort."""
    from src.cli import _run_generation

    result = asyncio.run(
        _run_generation(
            count=3,
            domain="saas",
            mode="quick",
            anchor_overrides={},
            persona_id_prefix="live",
            domain_data=None,
            sarvam_enabled=False,
            skip_gates=True,
        )
    )

    assert isinstance(result, dict), "Result must be a dict"
    assert "personas" in result, f"Expected 'personas' key, got: {list(result.keys())}"
    assert len(result["personas"]) == 3, (
        f"Expected 3 personas, got {len(result['personas'])}"
    )

    for persona in result["personas"]:
        assert "persona_id" in persona, f"Persona missing 'persona_id'"
        assert "demographic_anchor" in persona, f"Persona missing 'demographic_anchor'"
        assert "attributes" in persona, f"Persona missing 'attributes'"


@live
def test_live_simulate_cohort(tmp_path):
    """Run simulate on a saved cohort (uses real API)."""
    from src.cli import _run_generation, _run_simulation

    # Step 1: generate a 2-persona cohort and save it
    envelope_dict = asyncio.run(
        _run_generation(
            count=2,
            domain="cpg",
            mode="quick",
            anchor_overrides={},
            persona_id_prefix="live",
            domain_data=None,
            sarvam_enabled=False,
            skip_gates=True,
        )
    )
    cohort_path = _save_cohort(envelope_dict, tmp_path)

    # Step 2: create a scenario with 1 stimulus
    scenario_data = {
        "stimuli": ["You see a new snack product on the shelf. What do you think?"],
        "decision_scenario": None,
    }

    # Step 3: run simulation with 1 round
    result = asyncio.run(_run_simulation(cohort_path, scenario_data, rounds=1))

    assert isinstance(result, dict), "Result must be a dict"
    assert "results" in result, f"Expected 'results' key, got: {list(result.keys())}"
    assert len(result["results"]) == 2, (
        f"Expected 2 persona results, got {len(result['results'])}"
    )

    for entry in result["results"]:
        assert "persona_id" in entry, f"Entry missing 'persona_id'"
        assert "rounds" in entry, f"Entry missing 'rounds'"


@live
def test_live_survey_cohort(tmp_path):
    """Run survey on a saved cohort (uses real API)."""
    from src.cli import _run_generation, _run_survey

    # Step 1: generate a 2-persona cohort and save it
    envelope_dict = asyncio.run(
        _run_generation(
            count=2,
            domain="cpg",
            mode="quick",
            anchor_overrides={},
            persona_id_prefix="live",
            domain_data=None,
            sarvam_enabled=False,
            skip_gates=True,
        )
    )
    cohort_path = _save_cohort(envelope_dict, tmp_path)

    # Step 2: run a survey question
    result = asyncio.run(
        _run_survey(
            cohort_path,
            ["What is your favourite snack brand?"],
            model="claude-haiku-4-5-20251001",
        )
    )

    assert isinstance(result, dict), "Result must be a dict"
    assert "responses" in result, f"Expected 'responses' key, got: {list(result.keys())}"


@live
def test_live_full_pipeline(tmp_path):
    """Full pipeline: generate -> save -> load -> report -> survey."""
    from src.cli import _run_generation, _run_survey
    from src.persistence.envelope_store import load_envelope, save_envelope
    from src.reporting.cohort_report import format_cohort_report

    # Step 1: generate 3 CPG personas
    envelope_dict = asyncio.run(
        _run_generation(
            count=3,
            domain="cpg",
            mode="quick",
            anchor_overrides={},
            persona_id_prefix="live",
            domain_data=None,
            sarvam_enabled=False,
            skip_gates=True,
        )
    )

    # Step 2: save envelope to disk
    from src.schema.cohort import CohortEnvelope
    envelope_obj = CohortEnvelope.model_validate(envelope_dict)
    saved_path = save_envelope(envelope_obj, tmp_path / "cohort.json")

    # Step 3: load_envelope() round-trip
    loaded = load_envelope(saved_path)
    assert loaded is not None, "load_envelope returned None"
    assert len(loaded.personas) == 3, (
        f"Expected 3 personas after round-trip, got {len(loaded.personas)}"
    )

    # Step 4: format_cohort_report — assert len > 100
    report_text = format_cohort_report(loaded)
    assert len(report_text) > 100, (
        f"Report too short ({len(report_text)} chars), expected > 100"
    )

    # Step 5: run 1 survey question
    result = asyncio.run(
        _run_survey(
            str(saved_path),
            ["Which snack brand do you trust most?"],
            model="claude-haiku-4-5-20251001",
        )
    )

    assert isinstance(result, dict), "Survey result must be a dict"
    assert "responses" in result, (
        f"Expected 'responses' key in survey result, got: {list(result.keys())}"
    )
