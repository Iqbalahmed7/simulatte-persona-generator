# SPRINT 12 BRIEF — CURSOR
**Role:** Persistence Module + CLI `load` Command
**Sprint:** 12 — Persistence + Reporting
**Spec ref:** Master Spec §14C (v1 required: JSON output), CLI design
**Previous rating:** 20/20

---

## Context

The generator can produce a `CohortEnvelope` but has no way to save it to disk or load it back. Sprint 12 adds JSON persistence so the workflow becomes:
1. `generate` → saves `cohort.json`
2. `load` + `survey` → runs survey on a saved cohort (Sprint 12 Codex)

Your job: the persistence module and the CLI `load` command.

---

## File: `src/persistence/__init__.py`

```python
"""Simulatte Persona Generator — persistence layer.

Sprint 12. JSON file storage for CohortEnvelope.
"""
```

---

## File: `src/persistence/envelope_store.py`

```python
"""CohortEnvelope JSON persistence.

Sprint 12. Saves and loads CohortEnvelope to/from JSON files.
Uses model_dump() for serialisation and model_validate() for deserialisation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_envelope(envelope: Any, path: str | Path) -> Path:
    """Serialise a CohortEnvelope to a JSON file.

    Args:
        envelope: A CohortEnvelope instance.
        path: Destination file path (created or overwritten).

    Returns:
        The resolved Path where the file was written.
    """
    from src.schema.cohort import CohortEnvelope
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    data = envelope.model_dump(mode="json")
    with open(resolved, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return resolved


def load_envelope(path: str | Path) -> Any:
    """Load a CohortEnvelope from a JSON file.

    Args:
        path: Path to a JSON file previously written by save_envelope().

    Returns:
        A CohortEnvelope instance.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the JSON cannot be parsed into a CohortEnvelope.
    """
    from src.schema.cohort import CohortEnvelope
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Envelope file not found: {resolved}")
    with open(resolved, "r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        return CohortEnvelope.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Failed to parse envelope from {resolved}: {exc}") from exc


def envelope_summary(envelope: Any) -> str:
    """Return a brief human-readable summary of a CohortEnvelope.

    Used by CLI commands to print a one-line status after load/save.
    """
    n = len(envelope.personas)
    domain = envelope.domain
    cohort_id = envelope.cohort_id
    mode = envelope.mode
    return f"Cohort {cohort_id}: {n} persona(s), domain={domain}, mode={mode}"
```

---

## Add `load` command to `src/cli.py`

Add a second command to the existing CLI. Import `save_envelope` and `load_envelope` from `src.persistence.envelope_store`.

Also update the `generate` command to auto-save when `--output` is provided via `save_envelope` (replacing the raw `json.dumps` write with the persistence helper).

### `load` command:

```python
@cli.command()
@click.argument("path", type=click.Path(exists=True))
def load(path):
    """Load and summarise a saved CohortEnvelope JSON file."""
    from src.persistence.envelope_store import load_envelope, envelope_summary
    envelope = load_envelope(path)
    click.echo(envelope_summary(envelope))
    click.echo(f"  Personas: {[p.persona_id for p in envelope.personas]}")
```

### Update `generate` to use `save_envelope`:

In `_run_generation`, where the output file is written, replace the raw `json.dumps` call with:

```python
if output:
    from src.persistence.envelope_store import save_envelope
    saved_path = save_envelope(envelope_obj, output)
    click.echo(f"Cohort envelope saved to {saved_path}", err=True)
```

(Where `envelope_obj` is the `CohortEnvelope` before calling `model_dump()`.)

---

## File: `tests/test_persistence.py`

### Test 1: save_envelope creates file

```python
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
```

### Test 2: save then load round-trip

```python
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
```

### Test 3: load_envelope raises FileNotFoundError on missing file

```python
def test_load_envelope_missing_file(tmp_path):
    from src.persistence.envelope_store import load_envelope
    import pytest
    with pytest.raises(FileNotFoundError):
        load_envelope(tmp_path / "does_not_exist.json")
```

### Test 4: envelope_summary returns non-empty string

```python
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
```

### Test 5: CLI `load` command is registered

```python
def test_cli_load_command_registered():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["load", "--help"])
    assert result.exit_code == 0
    assert "PATH" in result.output.upper() or "path" in result.output.lower()
```

### Test 6: Saved JSON is valid JSON with personas key

```python
def test_saved_json_structure(tmp_path):
    import json
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
```

---

## Constraints

- No LLM calls.
- All 6 tests use `tmp_path` fixture (pytest built-in) — no disk pollution.
- `save_envelope` must work with `CohortEnvelope.model_dump(mode="json")` — use `mode="json"` to ensure all types (UUID, datetime, enum) are JSON-serialisable.
- Full suite must remain 186+ passed.

---

## Outcome File

Write `sprints/outcome_cursor.md` with:
1. Files created (line counts)
2. Round-trip fidelity approach
3. Test results (6/6)
4. Full suite result
5. Known gaps
