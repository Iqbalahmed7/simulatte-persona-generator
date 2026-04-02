# SPRINT 12 BRIEF — CODEX
**Role:** CLI `survey` Command + Survey Report CLI Integration
**Sprint:** 12 — Persistence + Reporting
**Spec ref:** Master Spec §1 (One-Time Survey Modality), existing `src/modalities/survey.py`
**Previous rating:** 19/20 (icp_spec_hash schema placement deviation — minor)

---

## Context

`src/modalities/survey.py` exists from Sprint 6 but is only accessible programmatically. Sprint 12 wires it into the CLI so users can: generate → save → survey.

Workflow:
```
python -m src.cli generate --spec spec.json --count 5 --output cohort.json
python -m src.cli survey --cohort cohort.json --questions questions.json --output report.json
```

Your job: the CLI `survey` command and a `questions.json` example file.

---

## Step 1: Read existing survey module

Read `src/modalities/survey.py` to understand the public API before writing the CLI command. Key things to find:
- What is the entry-point function signature? (probably `run_survey(cohort, questions, client)` or similar)
- What does it return? (probably a `SurveyReport` or list of responses)
- What is the `questions` format?

---

## Add `survey` command to `src/cli.py`

```python
@cli.command()
@click.option("--cohort", required=True, type=click.Path(exists=True),
              help="Path to saved CohortEnvelope JSON.")
@click.option("--questions", required=True, type=click.Path(exists=True),
              help="Path to JSON file containing survey questions (list of strings).")
@click.option("--output", default=None, help="Output JSON file for results (default: stdout).")
@click.option("--model", default="claude-haiku-4-5-20251001",
              help="LLM model for survey responses.")
def survey(cohort, questions, output, model):
    """Run a one-time survey on a saved cohort."""
    import asyncio
    import json
    import sys

    with open(questions) as f:
        question_list = json.load(f)

    if not isinstance(question_list, list):
        click.echo("Error: questions file must be a JSON array of strings.", err=True)
        sys.exit(1)

    result = asyncio.run(_run_survey(cohort, question_list, model))

    json_str = json.dumps(result, indent=2, default=str)
    if output:
        with open(output, "w") as f:
            f.write(json_str)
        click.echo(f"Survey results written to {output}")
    else:
        click.echo(json_str)


async def _run_survey(cohort_path: str, questions: list, model: str) -> dict:
    """Load cohort and run survey asynchronously."""
    import anthropic
    from src.persistence.envelope_store import load_envelope
    from src.modalities.survey import run_survey

    client = anthropic.AsyncAnthropic()
    envelope = load_envelope(cohort_path)

    click.echo(f"  Running survey on {len(envelope.personas)} persona(s)...", err=True)

    report = await run_survey(
        personas=envelope.personas,
        questions=questions,
        llm_client=client,
        model=model,
    )

    # Serialise to dict — handle both Pydantic models and plain dicts
    if hasattr(report, "model_dump"):
        return report.model_dump(mode="json")
    elif isinstance(report, dict):
        return report
    else:
        return {"report": str(report)}
```

**If `run_survey` has a different signature** than above, adapt the call to match what actually exists in `src/modalities/survey.py`. Don't guess — read the file first.

---

## File: `examples/questions_cpg.json`

Create an examples directory with a sample questions file:

```json
[
  "How do you typically decide which brand to buy when shopping for household essentials?",
  "What would make you switch from your current preferred brand to a new one?",
  "How important is price compared to quality when making purchase decisions?",
  "What role do recommendations from friends or family play in your purchasing decisions?",
  "Describe a recent purchase you made where you felt satisfied with your decision."
]
```

---

## File: `tests/test_cli_survey.py`

### Test 1: survey command is registered in CLI

```python
def test_survey_command_registered():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["survey", "--help"])
    assert result.exit_code == 0
    assert "--cohort" in result.output
    assert "--questions" in result.output
```

### Test 2: _run_survey is an async function

```python
def test_run_survey_is_async():
    import inspect
    from src.cli import _run_survey
    assert inspect.iscoroutinefunction(_run_survey)
```

### Test 3: questions file must be a JSON array

```python
def test_questions_json_structure(tmp_path):
    import json
    questions_file = tmp_path / "q.json"
    questions = [
        "How do you decide what to buy?",
        "What would make you switch brands?",
    ]
    questions_file.write_text(json.dumps(questions))
    loaded = json.loads(questions_file.read_text())
    assert isinstance(loaded, list)
    assert len(loaded) == 2
    assert all(isinstance(q, str) for q in loaded)
```

### Test 4: survey command fails gracefully on invalid questions format

```python
def test_survey_invalid_questions(tmp_path):
    import json
    from click.testing import CliRunner
    from src.cli import cli

    # Create a fake cohort file
    cohort_file = tmp_path / "cohort.json"
    cohort_file.write_text('{"cohort_id": "test"}')

    # Create an invalid questions file (not a list)
    bad_questions = tmp_path / "bad.json"
    bad_questions.write_text('{"not": "a list"}')

    runner = CliRunner()
    result = runner.invoke(cli, [
        "survey",
        "--cohort", str(cohort_file),
        "--questions", str(bad_questions),
    ])
    # Should exit with non-zero or print error
    assert result.exit_code != 0 or "error" in result.output.lower() or "Error" in result.output
```

### Test 5: examples/questions_cpg.json is valid JSON array

```python
def test_example_questions_file():
    import json
    from pathlib import Path
    path = Path("examples/questions_cpg.json")
    assert path.exists(), "examples/questions_cpg.json not created"
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) >= 3
    assert all(isinstance(q, str) for q in data)
```

---

## Constraints

- No LLM calls in tests.
- Read `src/modalities/survey.py` before implementing — adapt `_run_survey()` to the real API.
- `examples/` directory should be at project root (same level as `main.py`).
- `_run_survey` must be importable at module level (not nested inside click command).
- Full suite must remain 186+ passed.

---

## Outcome File

Write `sprints/outcome_codex.md` with:
1. Files created/modified (line counts)
2. Survey module API (what `run_survey` signature looks like)
3. Test results (5/5)
4. Full suite result
5. Known gaps
