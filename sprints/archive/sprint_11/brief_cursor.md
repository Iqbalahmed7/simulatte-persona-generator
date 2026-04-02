# SPRINT 11 BRIEF — CURSOR
**Role:** CLI Entry Point
**Sprint:** 11 — Production Entry Point + Technical Debt Clearance
**Spec ref:** Master Spec §14C (v1 required components), §1 (product modalities)
**Previous rating:** 20/20

---

## Context

Sprint 11 makes the persona generator usable. The full pipeline is built but has no user-facing entry point. Your job: build a CLI tool using Click that accepts a JSON spec file and produces a JSON persona envelope.

---

## File: `src/cli.py`

The single CLI entry point for the persona generator. Handles: ICP spec loading → persona generation (N personas, sequential async) → cohort assembly → JSON output.

```python
"""Simulatte Persona Generator — CLI entry point.

Sprint 11. Production entry point.

Usage:
  python -m src.cli generate --spec spec.json --count 5 --domain cpg
  python -m src.cli generate --spec spec.json --count 3 --domain saas --mode quick
  python -m src.cli generate --spec spec.json --count 1 --output envelope.json
"""
```

### Command: `generate`

```python
@click.command()
@click.option("--spec", required=True, type=click.Path(exists=True), help="Path to JSON spec file.")
@click.option("--count", default=5, type=int, help="Number of personas to generate (default: 5).")
@click.option("--domain", default="cpg", help="Domain: cpg | saas | general (default: cpg).")
@click.option("--mode", default="simulation-ready", help="Mode: quick | simulation-ready (default: simulation-ready).")
@click.option("--output", default=None, help="Output file path (default: stdout).")
@click.option("--sarvam", is_flag=True, default=False, help="Enable Sarvam enrichment (India market personas only).")
def generate(spec, count, domain, mode, output, sarvam):
    """Generate N personas from a JSON spec file and assemble a cohort envelope."""
    ...
```

### Spec file format (input JSON):

```json
{
  "anchor_overrides": {},
  "persona_id_prefix": "cpg-trial",
  "domain_data": null
}
```

All fields optional. If `domain_data` is a list of strings, grounding pipeline runs.

### Implementation:

```python
def generate(spec, count, domain, mode, output, sarvam):
    import asyncio
    import json
    import sys
    import anthropic

    # Load spec file
    with open(spec) as f:
        spec_data = json.load(f)

    anchor_overrides = spec_data.get("anchor_overrides", {})
    persona_id_prefix = spec_data.get("persona_id_prefix", "pg")
    domain_data = spec_data.get("domain_data", None)

    # Run async generation
    envelope_dict = asyncio.run(
        _run_generation(
            count=count,
            domain=domain,
            mode=mode,
            anchor_overrides=anchor_overrides,
            persona_id_prefix=persona_id_prefix,
            domain_data=domain_data,
            sarvam_enabled=sarvam,
        )
    )

    json_str = json.dumps(envelope_dict, indent=2, default=str)

    if output:
        with open(output, "w") as f:
            f.write(json_str)
        click.echo(f"Cohort envelope written to {output}")
    else:
        click.echo(json_str)


async def _run_generation(
    count: int,
    domain: str,
    mode: str,
    anchor_overrides: dict,
    persona_id_prefix: str,
    domain_data: list | None,
    sarvam_enabled: bool,
) -> dict:
    """Async inner function: builds N personas then assembles the cohort."""
    import anthropic
    from src.generation.identity_constructor import IdentityConstructor, ICPSpec
    from src.cohort.assembler import assemble_cohort

    client = anthropic.AsyncAnthropic()
    constructor = IdentityConstructor(client)

    personas = []
    for i in range(1, count + 1):
        icp = ICPSpec(
            domain=domain,
            mode=mode,
            anchor_overrides=anchor_overrides,
            persona_id_prefix=persona_id_prefix,
            persona_index=i,
            domain_data=domain_data,
        )
        persona = await constructor.build(icp)
        personas.append(persona)
        click.echo(f"  Generated persona {i}/{count}: {persona.persona_id}", err=True)

    envelope = assemble_cohort(
        personas=personas,
        domain=domain,
        domain_data=domain_data,
    )

    # Optional Sarvam enrichment
    if sarvam_enabled:
        from src.sarvam.config import SarvamConfig
        from src.sarvam.pipeline import run_sarvam_enrichment
        sarvam_config = SarvamConfig.enabled()
        enrichment_records = []
        for persona in personas:
            record = await run_sarvam_enrichment(persona, sarvam_config, client)
            enrichment_records.append(record.model_dump())
        return {
            "envelope": envelope.model_dump(),
            "sarvam_enrichment": enrichment_records,
        }

    return envelope.model_dump()
```

### Entry point wiring:

```python
@click.group()
def cli():
    """Simulatte Persona Generator CLI."""
    pass

cli.add_command(generate)

if __name__ == "__main__":
    cli()
```

### File: `main.py` (project root)

```python
"""Convenience entry point for python main.py generate ..."""
from src.cli import cli

if __name__ == "__main__":
    cli()
```

---

## File: `tests/test_cli.py`

### Test 1: CLI help returns 0

```python
def test_cli_help():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
```

### Test 2: generate --help

```python
def test_generate_help():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--spec" in result.output
    assert "--count" in result.output
    assert "--domain" in result.output
```

### Test 3: generate with missing spec file → non-zero exit

```python
def test_generate_missing_spec():
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--spec", "nonexistent_spec.json"])
    assert result.exit_code != 0
```

### Test 4: _run_generation is an async function

```python
def test_run_generation_is_async():
    import inspect
    from src.cli import _run_generation
    assert inspect.iscoroutinefunction(_run_generation)
```

### Test 5: spec file with valid JSON is loadable

```python
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
```

---

## Constraints

- No LLM calls in tests (Tests 1-5 are all structural).
- `click` is already installed (it's a pytest dependency).
- `_run_generation` must be importable for Test 4.
- `main.py` goes at project root (same level as `conftest.py`).
- Full suite must remain 155+ passed.

---

## Outcome File

Write `sprints/outcome_cursor.md` with:
1. Files created (line counts)
2. CLI command structure
3. Test results (5/5)
4. Full suite result
5. Known gaps
