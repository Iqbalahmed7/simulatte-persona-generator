"""Tests for Sprint 12 persistence module.

6 tests covering save_envelope, load_envelope, envelope_summary, and CLI load command.
"""
from __future__ import annotations

import json
import pytest


def test_save_envelope_creates_file(tmp_path):
    from src.persistence.envelope_store import save_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    output_path = tmp_path / "test_envelope.json"
    saved = save_envelope(envelope, output_path)
    assert saved.exists()
    assert saved.suffix == ".json"


def test_save_load_roundtrip(tmp_path):
    from src.persistence.envelope_store import save_envelope, load_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        original = assemble_cohort([persona], domain="cpg")

    path = tmp_path / "envelope.json"
    save_envelope(original, path)
    loaded = load_envelope(path)

    assert loaded.cohort_id == original.cohort_id
    assert len(loaded.personas) == len(original.personas)
    assert loaded.personas[0].persona_id == original.personas[0].persona_id


def test_load_envelope_missing_file(tmp_path):
    from src.persistence.envelope_store import load_envelope
    with pytest.raises(FileNotFoundError):
        load_envelope(tmp_path / "does_not_exist.json")


def test_envelope_summary(tmp_path):
    from src.persistence.envelope_store import save_envelope, load_envelope, envelope_summary
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    summary = envelope_summary(envelope)
    assert "cpg" in summary
    assert len(summary) > 10


def test_cli_load_command_registered():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["load", "--help"])
    assert result.exit_code == 0
    assert "PATH" in result.output.upper() or "path" in result.output.lower()


def test_saved_json_structure(tmp_path):
    from src.persistence.envelope_store import save_envelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    path = tmp_path / "envelope.json"
    save_envelope(envelope, path)

    with open(path) as f:
        data = json.load(f)

    assert "personas" in data
    assert "cohort_id" in data
    assert isinstance(data["personas"], list)
    assert len(data["personas"]) == 1
