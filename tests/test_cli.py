"""tests/test_cli.py — Structural tests for the CLI entry point.

Sprint 11. No LLM calls made in any of these tests.
"""


def test_cli_help():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output


def test_generate_help():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--spec" in result.output
    assert "--count" in result.output
    assert "--domain" in result.output


def test_generate_missing_spec():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--spec", "nonexistent_spec.json"])
    assert result.exit_code != 0


def test_run_generation_is_async():
    import inspect
    from src.cli import _run_generation
    assert inspect.iscoroutinefunction(_run_generation)


def test_spec_file_json_structure():
    """Verify the expected spec JSON structure can be parsed."""
    import json
    spec = {
        "anchor_overrides": {},
        "persona_id_prefix": "test",
        "domain_data": None
    }
    dumped = json.dumps(spec)
    loaded = json.loads(dumped)
    assert loaded["persona_id_prefix"] == "test"
    assert loaded["domain_data"] is None
    assert isinstance(loaded["anchor_overrides"], dict)
