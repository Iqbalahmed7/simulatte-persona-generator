# SPRINT 12 BRIEF — GOOSE
**Role:** Cohort Report Formatter
**Sprint:** 12 — Persistence + Reporting
**Spec ref:** Master Spec §1 (product outputs), CLI design
**Previous rating:** 20/20

---

## Context

A generated cohort envelope contains rich data but is raw JSON. Sprint 12 adds a human-readable text report formatter so users can share or print cohort summaries. This is pure formatting — no LLM calls.

---

## File: `src/reporting/__init__.py`

```python
"""Simulatte Persona Generator — reporting module.

Sprint 12. Human-readable report formatting for CohortEnvelope.
"""
```

---

## File: `src/reporting/cohort_report.py`

```python
"""Cohort report formatter.

Sprint 12. Generates a human-readable text report from a CohortEnvelope.
No LLM calls — pure formatting from existing persona fields.
"""
from __future__ import annotations

from typing import Any


def format_cohort_report(envelope: Any, include_narratives: bool = True) -> str:
    """Format a CohortEnvelope as a human-readable text report.

    Sections:
    1. Header — cohort_id, domain, mode, persona count, generation timestamp
    2. Cohort Summary — distinctiveness score, decision style distribution,
       trust anchor distribution, dominant tensions
    3. Per-Persona Profiles — for each persona:
       - Name, age, gender, location, income bracket
       - Decision style, trust anchor, risk appetite
       - Key tensions (up to 3)
       - First-person narrative (if include_narratives=True)
    4. Footer — taxonomy_meta: domain, domain_data_used, icp_spec_hash

    Args:
        envelope: A CohortEnvelope instance.
        include_narratives: Whether to include first-person narratives (default True).

    Returns:
        A formatted string suitable for printing or writing to a .txt file.
    """
    lines = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines.append("=" * 72)
    lines.append("SIMULATTE PERSONA COHORT REPORT")
    lines.append("=" * 72)
    lines.append(f"Cohort ID   : {envelope.cohort_id}")
    lines.append(f"Domain      : {envelope.domain}")
    lines.append(f"Mode        : {envelope.mode}")
    lines.append(f"Personas    : {len(envelope.personas)}")
    lines.append(f"Generated   : {envelope.generated_at}")
    lines.append("")

    # -----------------------------------------------------------------------
    # Cohort Summary
    # -----------------------------------------------------------------------
    s = envelope.cohort_summary
    lines.append("─" * 72)
    lines.append("COHORT SUMMARY")
    lines.append("─" * 72)
    lines.append(f"Distinctiveness score : {s.distinctiveness_score:.4f}")
    lines.append(f"Decision styles       : {_format_dist(s.decision_style_distribution)}")
    lines.append(f"Trust anchors         : {_format_dist(s.trust_anchor_distribution)}")
    lines.append(f"Risk appetites        : {_format_dist(s.risk_appetite_distribution)}")
    lines.append(f"Dominant tensions     : {', '.join(s.dominant_tensions[:3])}")
    lines.append(f"Persona types         : {_format_dist(s.persona_type_distribution)}")
    lines.append("")

    # -----------------------------------------------------------------------
    # Per-Persona Profiles
    # -----------------------------------------------------------------------
    lines.append("─" * 72)
    lines.append("PERSONA PROFILES")
    lines.append("─" * 72)

    for i, persona in enumerate(envelope.personas, 1):
        da = persona.demographic_anchor
        ins = persona.derived_insights
        bt = persona.behavioural_tendencies

        lines.append(f"\n[{i}] {da.name}  |  {persona.persona_id}")
        lines.append(
            f"    Age {da.age}, {da.gender.capitalize()}, "
            f"{da.location.city}, {da.location.country}"
        )
        lines.append(
            f"    {da.employment.capitalize()} · "
            f"{da.education.capitalize()} · "
            f"Income: {da.household.income_bracket}"
        )
        lines.append(f"    Decision style : {ins.decision_style}")
        lines.append(f"    Trust anchor   : {ins.trust_anchor}")
        lines.append(f"    Risk appetite  : {ins.risk_appetite}")
        if ins.key_tensions:
            tensions_str = " | ".join(ins.key_tensions[:3])
            lines.append(f"    Key tensions   : {tensions_str}")
        lines.append(
            f"    Price sensitivity : {bt.price_sensitivity.band.capitalize()}"
        )

        if include_narratives and persona.narrative:
            lines.append("")
            lines.append("    NARRATIVE (first-person):")
            # Wrap narrative at 68 chars
            for sentence in _wrap_text(persona.narrative.first_person, width=68, indent=4):
                lines.append(sentence)

    lines.append("")

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    tm = envelope.taxonomy_meta
    lines.append("─" * 72)
    lines.append("TAXONOMY METADATA")
    lines.append("─" * 72)
    lines.append(f"Domain            : {tm.domain}")
    lines.append(f"Domain data used  : {tm.domain_data_used}")
    lines.append(f"ICP spec hash     : {envelope.icp_spec_hash if hasattr(envelope, 'icp_spec_hash') else 'n/a'}")
    if tm.business_problem:
        lines.append(f"Business problem  : {tm.business_problem}")
    lines.append("=" * 72)

    return "\n".join(lines)


def _format_dist(dist: dict) -> str:
    """Format a distribution dict as 'key(N), key(N)' string."""
    if not dist:
        return "none"
    return ", ".join(f"{k}({v})" for k, v in sorted(dist.items(), key=lambda x: -x[1]))


def _wrap_text(text: str, width: int = 68, indent: int = 4) -> list[str]:
    """Wrap text at word boundaries, returning indented lines."""
    prefix = " " * indent
    words = text.split()
    lines = []
    current = prefix
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current.rstrip())
            current = prefix + word + " "
        else:
            current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return lines
```

---

## Add `report` command to `src/cli.py`

```python
@cli.command()
@click.argument("cohort_path", type=click.Path(exists=True))
@click.option("--output", default=None, help="Write report to this file (default: stdout).")
@click.option("--no-narratives", is_flag=True, default=False,
              help="Omit first-person narratives from report.")
def report(cohort_path, output, no_narratives):
    """Generate a human-readable text report from a saved cohort."""
    from src.persistence.envelope_store import load_envelope
    from src.reporting.cohort_report import format_cohort_report

    envelope = load_envelope(cohort_path)
    text = format_cohort_report(envelope, include_narratives=not no_narratives)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(text)
        click.echo(f"Report written to {output}")
    else:
        click.echo(text)
```

---

## File: `tests/test_cohort_report.py`

### Test 1: format_cohort_report returns a non-empty string

```python
def test_format_report_returns_string():
    from src.reporting.cohort_report import format_cohort_report
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    report = format_cohort_report(envelope)
    assert isinstance(report, str)
    assert len(report) > 100
```

### Test 2: report contains persona name and ID

```python
def test_report_contains_persona_info():
    from src.reporting.cohort_report import format_cohort_report
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    report = format_cohort_report(envelope)
    assert persona.persona_id in report
    assert persona.demographic_anchor.name in report
```

### Test 3: report without narratives is shorter

```python
def test_report_without_narratives_shorter():
    from src.reporting.cohort_report import format_cohort_report
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    with_narratives = format_cohort_report(envelope, include_narratives=True)
    without_narratives = format_cohort_report(envelope, include_narratives=False)
    assert len(with_narratives) > len(without_narratives)
```

### Test 4: _format_dist utility

```python
def test_format_dist():
    from src.reporting.cohort_report import _format_dist
    dist = {"analytical": 3, "emotional": 1, "intuitive": 2}
    result = _format_dist(dist)
    assert "analytical" in result
    assert "3" in result
    assert isinstance(result, str)
```

### Test 5: _wrap_text produces indented lines

```python
def test_wrap_text():
    from src.reporting.cohort_report import _wrap_text
    long_text = "This is a very long sentence that should be wrapped at a reasonable width for display purposes."
    lines = _wrap_text(long_text, width=50, indent=4)
    assert len(lines) > 1
    for line in lines:
        assert len(line) <= 50
        assert line.startswith("    ")
```

### Test 6: report command is registered in CLI

```python
def test_report_command_registered():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "cohort" in result.output.lower() or "COHORT" in result.output
```

---

## Constraints

- No LLM calls.
- All persona field accesses must use safe patterns — check what fields exist before using them. Read `src/schema/persona.py` and `src/schema/cohort.py` to confirm field names.
- `_format_dist`, `_wrap_text` must be importable (module-level functions, not nested).
- Full suite must remain 186+ passed.

---

## Outcome File

Write `sprints/outcome_goose.md` with:
1. Files created/modified (line counts)
2. Report sections overview
3. Test results (6/6)
4. Full suite result
5. Known gaps
