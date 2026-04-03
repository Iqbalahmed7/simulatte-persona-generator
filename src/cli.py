"""Simulatte Persona Generator — CLI entry point.

Sprint 12. Production entry point with persistence support.

Usage:
  python -m src.cli generate --spec spec.json --count 5 --domain cpg
  python -m src.cli generate --spec spec.json --count 3 --domain saas --mode quick
  python -m src.cli generate --spec spec.json --count 1 --output envelope.json
  python -m src.cli load envelope.json
"""

from __future__ import annotations

import click

# Load .env file automatically so ANTHROPIC_API_KEY is available
try:
    from dotenv import load_dotenv as _load_dotenv
    from pathlib import Path as _Path
    _env_file = _Path(__file__).parent.parent / ".env"
    _load_dotenv(dotenv_path=_env_file, override=True)
except ImportError:
    pass  # python-dotenv not installed — rely on shell env


@click.group()
def cli():
    """Simulatte Persona Generator CLI."""
    pass


@click.command()
@click.option("--spec", required=True, type=click.Path(exists=True), help="Path to JSON spec file.")
@click.option("--count", default=5, type=int, help="Number of personas to generate (default: 5).")
@click.option("--domain", default="cpg", help="Domain: cpg | saas | general (default: cpg).")
@click.option("--mode", default="quick", help="Mode: quick (fast, no seed memories) | simulation-ready (seeds working memory for cognitive loop). Default: quick.")
@click.option("--output", default=None, help="Output file path (default: stdout).")
@click.option("--sarvam", is_flag=True, default=False, help="Enable Sarvam enrichment (India market personas only).")
@click.option("--skip-gates", is_flag=True, default=False, help="Skip cohort-level quality gates (G6/G7/G8). Useful for development/testing.")
def generate(spec, count, domain, mode, output, sarvam, skip_gates):
    """Generate N personas from a JSON spec file and assemble a cohort envelope."""
    import asyncio
    import json

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
            skip_gates=skip_gates,
        )
    )

    if output:
        from src.persistence.envelope_store import save_envelope
        from src.schema.cohort import CohortEnvelope
        # If _run_generation returned a dict (normal path), save via JSON
        if isinstance(envelope_dict, dict) and "envelope" not in envelope_dict:
            import json as _json
            with open(output, "w", encoding="utf-8") as _f:
                _json.dump(envelope_dict, _f, indent=2, default=str)
            click.echo(f"Cohort envelope saved to {output}")
        else:
            click.echo(json.dumps(envelope_dict, indent=2, default=str))
    else:
        click.echo(json.dumps(envelope_dict, indent=2, default=str))


async def _run_generation(
    count: int,
    domain: str,
    mode: str,
    anchor_overrides: dict,
    persona_id_prefix: str,
    domain_data: list | None,
    sarvam_enabled: bool,
    skip_gates: bool = False,
) -> dict:
    """Async inner function: builds N personas then assembles the cohort."""
    import anthropic
    from src.generation.identity_constructor import IdentityConstructor, ICPSpec
    from src.cohort.assembler import assemble_cohort

    client = anthropic.AsyncAnthropic()
    constructor = IdentityConstructor(client)

    import asyncio
    from src.generation.demographic_sampler import sample_demographic_anchor

    async def _build_one(i: int):
        icp = ICPSpec(
            domain=domain,
            mode=mode,
            anchor_overrides=anchor_overrides,
            persona_id_prefix=persona_id_prefix,
            persona_index=i,
            domain_data=domain_data,
        )
        demographic_anchor = sample_demographic_anchor(domain=domain, index=i - 1)
        persona = await constructor.build(
            demographic_anchor=demographic_anchor,
            icp_spec=icp,
        )
        click.echo(f"  Generated persona {i}/{count}: {persona.persona_id} ({demographic_anchor.name})", err=True)
        return persona

    # Generate candidate pool (2× for stratification when count >= 5)
    pool_size = max(count * 2, count + 4) if count >= 5 else count
    candidates = list(await asyncio.gather(*[_build_one(i) for i in range(1, pool_size + 1)]))

    # Stratify if cohort is large enough
    if count >= 5 and len(candidates) > count:
        try:
            from src.generation.stratification import CohortStratifier
            stratifier = CohortStratifier()
            strat_result = stratifier.stratify(candidates, target_size=count)
            personas = strat_result.cohort
            click.echo(
                f"  Stratified to {count} personas (near={len(strat_result.near_center)},"
                f" mid={len(strat_result.mid_range)}, far={len(strat_result.far_outliers)})",
                err=True,
            )
        except ImportError:
            click.echo(
                "  Warning: numpy not available — skipping 5:3:2 stratification, using first"
                f" {count} candidates.",
                err=True,
            )
            personas = candidates[:count]
    else:
        personas = candidates[:count]

    envelope_obj = assemble_cohort(
        personas=personas,
        domain=domain,
        domain_data=domain_data,
        skip_gates=skip_gates,
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
            "envelope": envelope_obj.model_dump(mode="json"),
            "sarvam_enrichment": enrichment_records,
        }

    return envelope_obj.model_dump(mode="json")


cli.add_command(generate)


@click.command()
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
    import dataclasses
    from uuid import uuid4
    from src.persistence.envelope_store import load_envelope
    from src.modalities.survey import run_survey, SurveyQuestion

    envelope = load_envelope(cohort_path)

    click.echo(f"  Running survey on {len(envelope.personas)} persona(s)...", err=True)

    # Convert plain strings to SurveyQuestion objects
    survey_questions = [
        SurveyQuestion(id=f"q{i+1}", text=q if isinstance(q, str) else str(q))
        for i, q in enumerate(questions)
    ]

    report = await run_survey(
        questions=survey_questions,
        personas=envelope.personas,
    )

    # SurveyResult is a dataclass — serialise via dataclasses.asdict()
    if dataclasses.is_dataclass(report) and not isinstance(report, type):
        return dataclasses.asdict(report)
    elif hasattr(report, "model_dump"):
        return report.model_dump(mode="json")
    elif isinstance(report, dict):
        return report
    else:
        return {"report": str(report)}


cli.add_command(survey)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def load(path):
    """Load and summarise a saved CohortEnvelope JSON file."""
    from src.persistence.envelope_store import load_envelope, envelope_summary
    envelope = load_envelope(path)
    click.echo(envelope_summary(envelope))
    click.echo(f"  Personas: {[p.persona_id for p in envelope.personas]}")



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

@click.command()
@click.option("--cohort", required=True, type=click.Path(exists=True), help="Path to saved CohortEnvelope JSON.")
@click.option("--scenario", required=True, type=click.Path(exists=True), help="Path to scenario JSON file.")
@click.option("--rounds", default=1, type=int, help="Number of stimulus rounds per persona (default: 1).")
@click.option("--output", default=None, help="Output JSON file for results (default: stdout).")
@click.option(
    "--tier",
    default="deep",
    type=click.Choice(["deep", "signal", "volume"], case_sensitive=False),
    help=(
        "Simulation tier — controls model routing: "
        "deep (Haiku perceive, Sonnet reflect+decide, default), "
        "signal (Haiku perceive+reflect, Sonnet decide), "
        "volume (Haiku throughout, cheapest)."
    ),
)
def simulate(cohort, scenario, rounds, output, tier):
    """Run cognitive simulation on a saved cohort."""
    import asyncio
    import json

    with open(scenario) as f:
        scenario_data = json.load(f)

    result = asyncio.run(_run_simulation(cohort, scenario_data, rounds, tier=tier))

    json_str = json.dumps(result, indent=2, default=str)
    if output:
        with open(output, "w") as f:
            f.write(json_str)
        click.echo(f"Simulation results written to {output}")
    else:
        click.echo(json_str)


async def _run_simulation(cohort_path: str, scenario_data: dict, rounds: int, tier: str = "deep") -> dict:
    import asyncio
    from src.persistence.envelope_store import load_envelope
    from src.cognition.loop import run_loop
    from src.experiment.session import SimulationTier

    _tier = SimulationTier(tier.lower())

    envelope = load_envelope(cohort_path)
    stimuli = scenario_data.get("stimuli", [])
    decision_scenario = scenario_data.get("decision_scenario", None)

    # Cycle stimuli across rounds
    all_stimuli = (stimuli * ((rounds * len(stimuli) // len(stimuli)) + 1))[:rounds * max(len(stimuli), 1)]
    if not stimuli:
        all_stimuli = ["Observe the current market environment."] * rounds

    click.echo(f"  Simulating {len(envelope.personas)} persona(s) × {rounds} round(s) [tier={tier}]...", err=True)

    async def _simulate_persona(persona):
        import anthropic as _anthropic
        from src.utils.llm_router import get_llm_client
        _llm_base = _anthropic.AsyncAnthropic()
        country = persona.demographic_anchor.location.country if hasattr(persona.demographic_anchor, 'location') else None
        _icp_spec = getattr(envelope, 'icp_spec', None)
        sarvam_enabled = getattr(_icp_spec, 'sarvam_enabled', False) if _icp_spec else False
        _llm_client = get_llm_client(_llm_base, sarvam_enabled=sarvam_enabled, country=country)
        persona_results = {
            "persona_id": persona.persona_id,
            "persona_name": persona.demographic_anchor.name,
            "rounds": [],
        }
        current_persona = persona
        for round_num, stimulus in enumerate(all_stimuli[:rounds], 1):
            current_persona, loop_result = await run_loop(
                stimulus=stimulus,
                persona=current_persona,
                decision_scenario=decision_scenario if round_num == rounds else None,
                llm_client=_llm_client,
                tier=_tier,
            )
            round_data = {
                "round": round_num,
                "stimulus": stimulus,
                "observation_importance": loop_result.observation.importance,
                "reflected": loop_result.reflected,
                "decided": loop_result.decided,
            }
            if loop_result.decided and loop_result.decision:
                round_data["decision"] = loop_result.decision.decision
                round_data["confidence"] = loop_result.decision.confidence
                round_data["reasoning"] = loop_result.decision.reasoning_trace[:200]
            persona_results["rounds"].append(round_data)
        click.echo(f"    Done: {persona.persona_id}", err=True)
        return persona_results

    results = list(await asyncio.gather(*[_simulate_persona(p) for p in envelope.personas]))

    # Apply calibration
    from src.cohort.calibrator import compute_calibration_state
    calibration = compute_calibration_state(envelope, results)

    return {
        "simulation_id": f"sim-{__import__('uuid').uuid4().hex[:8]}",
        "cohort_id": envelope.cohort_id,
        "rounds": rounds,
        "decision_scenario": decision_scenario,
        "results": results,
        "calibration_state": {
            "status": calibration.status,
            "method_applied": calibration.method_applied,
            "consistency_score": float(calibration.notes.split("=")[1].split(";")[0]) if calibration.notes else None,
            "N": len(results),
        },
    }


cli.add_command(simulate)


# ---------------------------------------------------------------------------
# age-persona — Longitudinal Persona Aging
# ---------------------------------------------------------------------------

@click.command("age-persona")
@click.option(
    "--persona-id",
    required=True,
    help="persona_id to run the annual review for (e.g. pg-001).",
)
@click.option(
    "--history-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to a JSON file containing a list of CohortEnvelope records "
         "that form the simulation history for this persona.",
)
def age_persona(persona_id: str, history_path: str) -> None:
    """Run an annual aging review for a persona across its simulation history.

    Scans high-importance reflections (importance >= 8), clusters them by
    semantic theme, and attempts to promote qualifying clusters to core memory
    using the standard promotion gate (importance >= 9, no contradiction).

    Demographics and life-defining events are never promoted (S17).

    Output: JSON AgingReport written to stdout.
    """
    import json
    from pathlib import Path
    from src.memory.aging import run_annual_review
    from src.schema.persona import PersonaRecord

    history_file = Path(history_path)
    with open(history_file, encoding="utf-8") as f:
        raw_history = json.load(f)

    # raw_history may be a single envelope or a list of envelopes
    if isinstance(raw_history, dict):
        raw_history = [raw_history]

    # Find the target persona across all envelopes in the history
    target_persona: PersonaRecord | None = None
    for envelope_raw in raw_history:
        personas_raw = (
            envelope_raw.get("personas", [])
            if isinstance(envelope_raw, dict)
            else []
        )
        for p_raw in personas_raw:
            try:
                p = PersonaRecord.model_validate(p_raw)
                if p.persona_id == persona_id:
                    target_persona = p
                    break
            except Exception:
                pass
        if target_persona is not None:
            break

    if target_persona is None:
        click.echo(
            json.dumps({"error": f"persona_id '{persona_id}' not found in history file"}),
            err=True,
        )
        raise SystemExit(1)

    report = run_annual_review(target_persona, raw_history)

    output = {
        "persona_id": report.persona_id,
        "reflections_reviewed": report.reflections_reviewed,
        "promotions_attempted": report.promotions_attempted,
        "promotions_succeeded": report.promotions_succeeded,
        "promotions_blocked": report.promotions_blocked,
        "summary": report.summary(),
    }
    click.echo(json.dumps(output, indent=2))


cli.add_command(age_persona)


if __name__ == "__main__":
    cli()
