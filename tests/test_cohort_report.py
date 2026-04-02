"""tests/test_cohort_report.py — Sprint 12 tests for cohort report formatter.

6 tests covering format_cohort_report, _format_dist, _wrap_text, and CLI registration.
No LLM calls.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Test 1: format_cohort_report returns a non-empty string
# ---------------------------------------------------------------------------
def test_format_report_returns_string():
    from src.reporting.cohort_report import format_cohort_report
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock()
        m.return_value.run_all.return_value = []
        return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    result = format_cohort_report(envelope)
    assert isinstance(result, str)
    assert len(result) > 100


# ---------------------------------------------------------------------------
# Test 2: report contains persona name and ID
# ---------------------------------------------------------------------------
def test_report_contains_persona_info():
    from src.reporting.cohort_report import format_cohort_report
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock()
        m.return_value.run_all.return_value = []
        return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    result = format_cohort_report(envelope)
    assert persona.persona_id in result
    assert persona.demographic_anchor.name in result


# ---------------------------------------------------------------------------
# Test 3: report without narratives is shorter
# ---------------------------------------------------------------------------
def test_report_without_narratives_shorter():
    from src.reporting.cohort_report import format_cohort_report
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock()
        m.return_value.run_all.return_value = []
        return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    with_narratives = format_cohort_report(envelope, include_narratives=True)
    without_narratives = format_cohort_report(envelope, include_narratives=False)
    assert len(with_narratives) > len(without_narratives)


# ---------------------------------------------------------------------------
# Test 4: _format_dist utility
# ---------------------------------------------------------------------------
def test_format_dist():
    from src.reporting.cohort_report import _format_dist

    dist = {"analytical": 3, "emotional": 1, "intuitive": 2}
    result = _format_dist(dist)
    assert "analytical" in result
    assert "3" in result
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Test 5: _wrap_text produces indented lines
# ---------------------------------------------------------------------------
def test_wrap_text():
    from src.reporting.cohort_report import _wrap_text

    long_text = (
        "This is a very long sentence that should be wrapped at a reasonable "
        "width for display purposes."
    )
    lines = _wrap_text(long_text, width=50, indent=4)
    assert len(lines) > 1
    for line in lines:
        assert len(line) <= 50
        assert line.startswith("    ")


# ---------------------------------------------------------------------------
# Test 6: report command is registered in CLI
# ---------------------------------------------------------------------------
def test_report_command_registered():
    from click.testing import CliRunner
    from src.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "cohort" in result.output.lower() or "COHORT" in result.output
