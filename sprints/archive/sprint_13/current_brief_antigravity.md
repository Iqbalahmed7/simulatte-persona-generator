# SPRINT 12 BRIEF — ANTIGRAVITY
**Role:** End-to-End CLI Integration Tests + Persistence Gate Tests
**Sprint:** 12 — Persistence + Reporting
**Spec ref:** Validity Protocol (full pipeline integrity), CLI design
**Previous rating:** 20/20

---

## Context

Sprint 12 delivers persistence, reporting, and a new domain template. Your job: write the end-to-end CLI integration tests that verify the complete user workflow (generate → save → load → report) works structurally.

---

## File: `tests/test_cli_integration.py`

All tests use `tmp_path` fixture, Click's `CliRunner`, and the synthetic persona fixture. No LLM calls.

### Test 1: generate command writes JSON file via persistence

```python
def test_generate_writes_json(tmp_path):
    """generate --output saves a valid JSON file."""
    import json
    from click.testing import CliRunner
    from src.cli import cli
    from unittest.mock import patch, AsyncMock, MagicMock

    spec_file = tmp_path / "spec.json"
    spec_file.write_text('{"anchor_overrides": {}, "persona_id_prefix": "test"}')
    output_file = tmp_path / "cohort.json"

    # Mock the async generation so no LLM call is made
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    with patch("src.cli._run_generation", new=AsyncMock(return_value=envelope.model_dump(mode="json"))):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--spec", str(spec_file),
            "--count", "1",
            "--domain", "cpg",
            "--output", str(output_file),
        ])

    assert output_file.exists(), f"Output file not created. CLI output: {result.output}"
    with open(output_file) as f:
        data = json.load(f)
    assert "personas" in data or "cohort_id" in data
```

### Test 2: load command reads saved envelope

```python
def test_load_command_reads_envelope(tmp_path):
    """load command prints envelope summary for a saved cohort."""
    from click.testing import CliRunner
    from src.cli import cli
    from src.persistence.envelope_store import save_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    saved_path = tmp_path / "cohort.json"
    save_envelope(envelope, saved_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["load", str(saved_path)])

    assert result.exit_code == 0
    assert "cpg" in result.output.lower() or envelope.cohort_id in result.output
```

### Test 3: report command generates text report

```python
def test_report_command_generates_text(tmp_path):
    """report command outputs a text report from a saved cohort."""
    from click.testing import CliRunner
    from src.cli import cli
    from src.persistence.envelope_store import save_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    saved_path = tmp_path / "cohort.json"
    save_envelope(envelope, saved_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["report", str(saved_path)])

    assert result.exit_code == 0
    assert "SIMULATTE" in result.output or "COHORT" in result.output
    assert len(result.output) > 200
```

### Test 4: report --output writes to file

```python
def test_report_writes_to_file(tmp_path):
    """report --output writes the report to a file."""
    from click.testing import CliRunner
    from src.cli import cli
    from src.persistence.envelope_store import save_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    saved_path = tmp_path / "cohort.json"
    report_path = tmp_path / "report.txt"
    save_envelope(envelope, saved_path)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "report", str(saved_path),
        "--output", str(report_path),
    ])

    assert result.exit_code == 0
    assert report_path.exists()
    content = report_path.read_text()
    assert len(content) > 200
```

### Test 5: generate → save → load round-trip preserves persona count

```python
def test_generate_save_load_roundtrip(tmp_path):
    """Round-trip: assemble cohort → save_envelope → load_envelope → persona count matches."""
    from src.persistence.envelope_store import save_envelope, load_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        original = assemble_cohort([persona], domain="cpg")

    path = tmp_path / "cohort.json"
    save_envelope(original, path)
    loaded = load_envelope(path)

    assert loaded.cohort_id == original.cohort_id
    assert len(loaded.personas) == len(original.personas)
    assert loaded.domain == original.domain
```

### Test 6: CLI has generate, load, survey, report commands

```python
def test_all_commands_registered():
    """All four CLI commands must be registered."""
    from click.testing import CliRunner
    from src.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "generate" in result.output
    assert "load" in result.output
    assert "report" in result.output
    # survey may not be present if Codex hasn't finished — check gracefully
    # (test 6 only hard-requires generate/load/report)
```

### Test 7: save_envelope + load_envelope preserves derived_insights

```python
def test_roundtrip_preserves_derived_insights(tmp_path):
    """DerivedInsights fields must survive JSON round-trip."""
    from src.persistence.envelope_store import save_envelope, load_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        original = assemble_cohort([persona], domain="cpg")

    path = tmp_path / "cohort.json"
    save_envelope(original, path)
    loaded = load_envelope(path)

    orig_ins = original.personas[0].derived_insights
    load_ins = loaded.personas[0].derived_insights
    assert orig_ins.decision_style == load_ins.decision_style
    assert orig_ins.trust_anchor == load_ins.trust_anchor
    assert orig_ins.risk_appetite == load_ins.risk_appetite
```

### Test 8: health_wellness domain template is loadable

```python
def test_hw_template_loadable():
    """Health & Wellness template must be importable and have attributes."""
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_TEMPLATE
    assert HEALTH_WELLNESS_TEMPLATE.domain == "health_wellness"
    assert len(HEALTH_WELLNESS_TEMPLATE.attributes) >= 20
```

---

## Constraints

- No LLM calls. Use mocks for `_run_generation` in Test 1.
- All file operations use `tmp_path` — no disk pollution.
- Tests 2–5, 7 depend on Cursor's `save_envelope`/`load_envelope` — these must already exist.
- Test 3 depends on Goose's `format_cohort_report` being wired into the `report` CLI command.
- Test 8 depends on OpenCode's `health_wellness.py`.
- 8 tests, run the suite after all other engineers complete. Note any failures from missing dependencies in the outcome file.
- Full suite target: 218+ passed (186 base + ~32 new from all Sprint 12 engineers).

---

## Outcome File

Write `sprints/outcome_antigravity.md` with:
1. File created (line count)
2. Which tests passed / which required waiting for other engineers
3. Test results (8/8 target)
4. Full suite result
5. Any schema/API adaptations required
