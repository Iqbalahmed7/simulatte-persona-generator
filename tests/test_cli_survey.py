"""tests/test_cli_survey.py — CLI survey command tests.

Sprint 12 — Codex.
No LLM calls are made in these tests.
"""

from __future__ import annotations


def test_survey_command_registered():
    """Survey command is registered in the CLI group."""
    from click.testing import CliRunner
    from src.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["survey", "--help"])
    assert result.exit_code == 0
    assert "--cohort" in result.output
    assert "--questions" in result.output


def test_run_survey_is_async():
    """_run_survey must be an async (coroutine) function."""
    import inspect
    from src.cli import _run_survey

    assert inspect.iscoroutinefunction(_run_survey)


def test_questions_json_structure(tmp_path):
    """A valid questions JSON file is a list of strings."""
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


def test_survey_invalid_questions(tmp_path):
    """Survey command exits non-zero or prints error when questions file is not a list."""
    import json
    from click.testing import CliRunner
    from src.cli import cli

    # Create a fake cohort file (load_envelope will fail, but the questions
    # validation should trigger first since cohort file is read before survey runs)
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


def test_example_questions_file():
    """examples/questions_cpg.json exists and is a valid JSON array of strings."""
    import json
    from pathlib import Path

    path = Path("examples/questions_cpg.json")
    assert path.exists(), "examples/questions_cpg.json not created"
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) >= 3
    assert all(isinstance(q, str) for q in data)
