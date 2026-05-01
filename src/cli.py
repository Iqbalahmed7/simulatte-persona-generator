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
from pathlib import Path

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
@click.option("--registry-path", default=None, help="Path to persona registry. If provided, reuses matching personas before generating new ones.")
def generate(spec, count, domain, mode, output, sarvam, skip_gates, registry_path):
    """Generate N personas from a JSON spec file and assemble a cohort envelope."""
    import asyncio
    import json

    # Load spec file
    with open(spec) as f:
        spec_data = json.load(f)

    anchor_overrides = spec_data.get("anchor_overrides", {})
    persona_id_prefix = spec_data.get("persona_id_prefix", "pg")
    domain_data = spec_data.get("domain_data", None)
    spec_client = spec_data.get("client", "")  # stored in envelope for automatic G12 resolution

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
            registry_path=registry_path,
            client=spec_client,
        )
    )

    if output:
        # Write to file regardless of envelope structure
        import json as _json
        with open(output, "w", encoding="utf-8") as _f:
            _json.dump(envelope_dict, _f, indent=2, default=str)
        click.echo(f"Cohort envelope saved to {output}", err=True)
        if False:  # retained to keep unused imports from breaking dependents
            from src.persistence.envelope_store import save_envelope
            from src.schema.cohort import CohortEnvelope
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
    registry_path: str | None = None,
    client: str = "",
    streaming_writer: "StreamingCohortWriter | None" = None,  # type: ignore[name-defined]
    max_attempts: int = 2,
) -> dict:
    """Async inner function: builds N personas then assembles the cohort.

    When *streaming_writer* is provided (or auto-triggered above
    ``StreamingCohortWriter.STREAMING_THRESHOLD``), personas are written to
    disk immediately as they complete rather than held entirely in memory.
    This provides two benefits:

    - **Checkpoint resilience**: a crash after persona #22 of 30 can be
      resumed from the last checkpoint rather than starting over.
    - **LLM-agent efficiency**: when the Persona Generator skill (Claude Code)
      is generating personas as text, it can produce one at a time and call
      ``writer.append()`` between them, avoiding context-limit errors.

    Pass an explicit ``StreamingCohortWriter`` instance to control output
    location and cohort_id.  If ``streaming_writer=None`` and
    ``count >= StreamingCohortWriter.STREAMING_THRESHOLD``, a writer is
    created automatically using a temp directory.
    """
    from src.persistence.streaming_writer import StreamingCohortWriter
    import anthropic
    from src.generation.identity_constructor import IdentityConstructor, ICPSpec
    from src.cohort.assembler import assemble_cohort

    import os
    # Rename to llm_client to avoid shadowing the `client: str` name param above
    llm_client = anthropic.AsyncAnthropic()
    # GENERATION_MODEL env var allows switching between Sonnet (quality) and
    # Haiku (cost-efficient). Default: claude-sonnet-4-6 for generation fidelity.
    # Set GENERATION_MODEL=claude-haiku-4-5-20251001 to reduce cost at the expense
    # of attribute coherence (Sprint A-3 showed −3 to −25pp accuracy with Haiku).
    generation_model = os.getenv("GENERATION_MODEL", "claude-sonnet-4-6")
    constructor = IdentityConstructor(llm_client, model=generation_model)

    import asyncio
    import threading as _threading
    from src.generation.demographic_sampler import sample_demographic_anchor

    # Build a synchronous regenerate_failing callable that replaces the entire
    # persona list by running LLM generation in an isolated thread (avoids the
    # nested-event-loop restriction when called from the sync assemble_cohort).
    def _regenerate_failing(
        personas: list,
        failing_results: list,
        attempt: int,
    ) -> list:
        n = len(personas)
        _results: list = []
        _exc: list = []

        async def _regen_async() -> list:
            tasks = []
            for i in range(n):
                icp = ICPSpec(
                    domain=domain,
                    mode=mode,
                    anchor_overrides=anchor_overrides,
                    persona_id_prefix=f"{persona_id_prefix}-r{attempt}",
                    persona_index=i + 1,
                    domain_data=domain_data,
                )
                anchor = sample_demographic_anchor(
                    domain=domain,
                    index=i,
                    anchor_overrides=anchor_overrides,
                )
                tasks.append(constructor.build(demographic_anchor=anchor, icp_spec=icp))
            return await asyncio.gather(*tasks, return_exceptions=True)

        def _thread_fn() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                _results.extend(loop.run_until_complete(_regen_async()))
            except Exception as exc:  # noqa: BLE001
                _exc.append(exc)
            finally:
                loop.close()

        t = _threading.Thread(target=_thread_fn, daemon=True)
        t.start()
        t.join(timeout=300)

        if _exc:
            click.echo(
                f"  [regenerate_failing] attempt {attempt} error: {_exc[0]}; keeping originals",
                err=True,
            )
            return personas

        from src.schema.persona import PersonaRecord as _PR
        valid = [p for p in _results if isinstance(p, _PR)]
        if not valid:
            click.echo(
                f"  [regenerate_failing] attempt {attempt}: no valid personas produced; keeping originals",
                err=True,
            )
            return personas

        click.echo(
            f"  [regenerate_failing] attempt {attempt}: regenerated {len(valid)}/{n} persona(s)",
            err=True,
        )
        return valid

    # ------------------------------------------------------------------
    # Registry hook — reuse matching personas before generating new ones
    # ------------------------------------------------------------------
    registry_personas: list = []
    generate_count = count

    if registry_path is not None:
        from src.registry.registry_assembler import assemble_from_registry
        from src.registry.persona_registry import PersonaRegistry
        registry_obj = PersonaRegistry(registry_path)
        assembly = assemble_from_registry(
            registry=registry_obj,
            icp_age_min=20,
            icp_age_max=60,
            new_domain=domain,
            target_count=count,
            icp_gender=None,
            icp_city_tier=None,
        )
        registry_personas = assembly.reused_personas
        generate_count = assembly.gap_count
        click.echo(
            f"  Registry: reused={assembly.reused_personas.__len__()} gap={assembly.gap_count}"
            f" (drift_filtered={assembly.drift_filtered_count})",
            err=True,
        )

    async def _build_one(i: int):
        icp = ICPSpec(
            domain=domain,
            mode=mode,
            anchor_overrides=anchor_overrides,
            persona_id_prefix=persona_id_prefix,
            persona_index=i,
            domain_data=domain_data,
        )
        pool_index_base = anchor_overrides.get("pool_index", 0)
        demographic_anchor = sample_demographic_anchor(domain=domain, index=pool_index_base + (i - 1), anchor_overrides=anchor_overrides)
        persona = await constructor.build(
            demographic_anchor=demographic_anchor,
            icp_spec=icp,
        )
        click.echo(f"  Generated persona {i}/{generate_count}: {persona.persona_id} ({demographic_anchor.name})", err=True)
        return persona

    # ------------------------------------------------------------------
    # Determine whether to use streaming writes
    # ------------------------------------------------------------------
    # Streaming is activated when:
    #   (a) an explicit streaming_writer was passed in, OR
    #   (b) the requested count is at or above STREAMING_THRESHOLD
    # In case (b) we create an auto writer using a temp directory.
    _auto_writer_created = False
    if streaming_writer is None and StreamingCohortWriter.should_stream(count):
        import tempfile, uuid as _uuid
        _tmp_dir = Path(tempfile.mkdtemp(prefix="pg_stream_"))
        _cohort_id = f"cohort-{domain}-{_uuid.uuid4().hex[:8]}"
        streaming_writer = StreamingCohortWriter(_tmp_dir, _cohort_id)
        streaming_writer.begin({"cohort_id": _cohort_id, "domain": domain, "client": client})
        _auto_writer_created = True
        click.echo(
            f"  [streaming] Auto-activated (count={count} >= "
            f"threshold={StreamingCohortWriter.STREAMING_THRESHOLD}). "
            f"Checkpointing to {streaming_writer.staging_dir}",
            err=True,
        )

    # ------------------------------------------------------------------
    # Generate candidate pool for newly needed personas
    # (skip generation entirely if registry already covers full demand)
    # ------------------------------------------------------------------
    newly_generated_personas: list = []
    if generate_count > 0:
        # Generate candidate pool (2× for stratification when generate_count >= 5)
        pool_size = max(generate_count * 2, generate_count + 4) if generate_count >= 5 else generate_count

        # Bound concurrency to avoid saturating Anthropic rate limits.
        # Each _build_one makes ~15-20 sequential API calls; at 10 concurrent
        # builds that's ~150-200 in-flight requests — within safe limits.
        # For large Niobe runs (500+ personas) unbounded concurrency causes all
        # tasks to enter retry loops simultaneously and the event loop never drains.
        # Override via PG_MAX_CONCURRENT_BUILDS env var.
        _max_concurrent = int(os.getenv("PG_MAX_CONCURRENT_BUILDS", "10"))
        _sem = asyncio.Semaphore(_max_concurrent)

        async def _build_bounded(i: int):
            async with _sem:
                return await _build_one(i)

        if streaming_writer is not None:
            # ---- Streaming path: use as_completed so each persona is written
            #      to disk the moment it finishes, regardless of overall order.
            # Note: stratification still runs after all candidates are collected;
            # the pre-stratification candidates are checkpointed, and the final
            # selected set is what gets embedded in the cohort envelope.
            tasks = [asyncio.create_task(_build_bounded(i)) for i in range(1, pool_size + 1)]
            candidates = []
            for coro in asyncio.as_completed(tasks):
                p = await coro
                streaming_writer.append(p.model_dump(mode="json"))
                candidates.append(p)
        else:
            # ---- Batch path (original behaviour)
            candidates = list(await asyncio.gather(*[_build_bounded(i) for i in range(1, pool_size + 1)]))

        # Stratify if cohort is large enough
        if generate_count >= 5 and len(candidates) > generate_count:
            try:
                from src.generation.stratification import CohortStratifier
                stratifier = CohortStratifier()
                strat_result = stratifier.stratify(candidates, target_size=generate_count)
                newly_generated_personas = strat_result.cohort
                click.echo(
                    f"  Stratified to {generate_count} personas (near={len(strat_result.near_center)},"
                    f" mid={len(strat_result.mid_range)}, far={len(strat_result.far_outliers)})",
                    err=True,
                )
            except ImportError:
                click.echo(
                    "  Warning: numpy not available — skipping 5:3:2 stratification, using first"
                    f" {generate_count} candidates.",
                    err=True,
                )
                newly_generated_personas = candidates[:generate_count]
        else:
            newly_generated_personas = candidates[:generate_count]

    # Assemble full cohort: registry personas + newly generated
    personas = registry_personas + newly_generated_personas

    # Defensive check: ensure we have personas before assembly
    if not personas:
        raise RuntimeError(
            f"Generation pipeline produced 0 personas. "
            f"Registry: {len(registry_personas)}, "
            f"Generated: {len(newly_generated_personas)}, "
            f"Generate count was: {generate_count}. "
            f"This indicates a failure in persona generation or stratification."
        )

    envelope_obj = assemble_cohort(
        personas=personas,
        domain=domain,
        domain_data=domain_data,
        client=client,
        skip_gates=skip_gates,
        regenerate_failing=_regenerate_failing,
        max_attempts=max_attempts,
    )

    # ------------------------------------------------------------------
    # If auto writer was created, finalize it now
    # (explicit writers are finalized by the orchestrator, which can set
    #  the cohort_id and output path correctly before calling finalize())
    # ------------------------------------------------------------------
    if _auto_writer_created and streaming_writer is not None:
        envelope_dict_for_summary = envelope_obj.model_dump(mode="json")
        streaming_writer.finalize(
            cohort_summary=envelope_dict_for_summary.get("cohort_summary"),
            overwrite=True,
        )

    # Persist newly generated personas back to registry (if registry in use)
    if registry_path is not None and newly_generated_personas:
        from src.registry.persona_registry import PersonaRegistry
        reg = PersonaRegistry(registry_path)
        for p in newly_generated_personas:
            reg.add(p)

    # Optional Sarvam enrichment
    if sarvam_enabled:
        from src.sarvam.config import SarvamConfig
        from src.sarvam.pipeline import run_sarvam_enrichment
        sarvam_config = SarvamConfig.enabled()
        enrichment_records = []
        for persona in personas:
            record = await run_sarvam_enrichment(persona, sarvam_config, llm_client)
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
@click.option("--calibrate", is_flag=True, default=False,
    help="Run benchmark calibration after simulation (requires --benchmark-conversion and --benchmark-wtp-median)")
@click.option("--benchmark-conversion", type=float, default=None,
    help="Known real-world conversion rate (0.0-1.0) for C3 calibration gate")
@click.option("--benchmark-wtp-median", type=float, default=None,
    help="Known real-world median WTP for calibration")
@click.option("--social-level", default="isolated",
              type=click.Choice(["isolated","low","moderate","high","saturated"], case_sensitive=False),
              help="Social simulation level (default: isolated = no peer influence).")
@click.option("--social-topology", default="random_encounter",
              type=click.Choice(["full_mesh","random_encounter"], case_sensitive=False),
              help="Network topology for peer influence (default: random_encounter).")
@click.option("--skip-grounding-check", is_flag=True, default=False,
              help="Skip the automatic G12 Simulation Grounding Check (dev/test use only).")
def simulate(cohort, scenario, rounds, output, tier, calibrate, benchmark_conversion, benchmark_wtp_median, social_level, social_topology, skip_grounding_check):
    """Run cognitive simulation on a saved cohort.

    G12 Grounding Check runs automatically after every simulation.
    The client is resolved from the cohort envelope (set when the cohort was
    generated from a spec file with a 'client' field).  If the client cannot be
    resolved, G12 is skipped with a warning — add a 'client' key to your spec
    file to enable automatic grounding validation.
    """
    import asyncio
    import json

    with open(scenario) as f:
        scenario_data = json.load(f)

    result = asyncio.run(_run_simulation(cohort, scenario_data, rounds, tier=tier,
                                          social_level=social_level, social_topology=social_topology))

    # -------------------------------------------------------------------------
    # G12 — Simulation Grounding Check (automatic on every simulate run)
    # Client is read from the cohort envelope — no flag required.
    # Use --skip-grounding-check only for dev/test scenarios.
    # -------------------------------------------------------------------------
    if not skip_grounding_check:
        try:
            from src.validation.grounding_check import run_grounding_check, load_market_facts
            from src.persistence.envelope_store import load_envelope

            _env = load_envelope(cohort)
            g12_client = getattr(_env, "client", "") or ""

            if not g12_client:
                click.echo(
                    "[G12] No client found in cohort envelope — skipping grounding check. "
                    "Add a 'client' field to your spec file (e.g. \"client\": \"lumio\") "
                    "to enable automatic G12 validation.",
                    err=True,
                )
            else:
                market_facts = load_market_facts(g12_client)

                # Build product_frame: all stimuli + decision scenario from the scenario file
                product_frame = " ".join(str(s) for s in scenario_data.get("stimuli", []))
                if scenario_data.get("decision_scenario"):
                    product_frame += " " + str(scenario_data["decision_scenario"])

                # Build persona_outputs: narrative fields from envelope + verbatim quotes from results
                envelope_personas = {p.persona_id: p for p in _env.personas}
                persona_outputs = []
                for r in result.get("results", []):
                    pid = r.get("persona_id")
                    persona_dict = {"persona_id": pid}
                    p_record = envelope_personas.get(pid)
                    if p_record:
                        if getattr(p_record, "narrative", None):
                            persona_dict["narrative"] = p_record.narrative
                        if getattr(p_record, "first_person_summary", None):
                            persona_dict["first_person_summary"] = p_record.first_person_summary
                    quotes = []
                    for rnd in r.get("rounds", []):
                        if rnd.get("response"):
                            quotes.append(rnd["response"])
                        if rnd.get("reasoning"):
                            quotes.append(rnd["reasoning"])
                    if quotes:
                        persona_dict["quotes"] = quotes
                    persona_outputs.append(persona_dict)

                g12_report = run_grounding_check(
                    product_frame=product_frame,
                    market_facts=market_facts,
                    persona_outputs=persona_outputs,
                )

                # Embed G12 results in the simulation output JSON
                result["grounding_check"] = {
                    "client": g12_client,
                    "passed": g12_report.passed,
                    "issue_count": len(g12_report.issues),
                    "clean_count": g12_report.clean_count,
                    "issues": [
                        {
                            "type": i.issue_type,
                            "severity": i.severity,
                            "persona_id": i.persona_id,
                            "location": i.location,
                            "contaminated_text": i.contaminated_text,
                            "reason": i.reason,
                            "suggested_fix": i.suggested_fix,
                        }
                        for i in g12_report.issues
                    ],
                }

                # Always print summary to stderr so it's visible without polluting JSON output
                click.echo("", err=True)
                click.echo(g12_report.summary(), err=True)
                click.echo("", err=True)
                if not g12_report.passed:
                    click.echo(
                        "[G12] FAIL — fix contamination issues before building reports.",
                        err=True,
                    )
                else:
                    click.echo(f"[G12] PASS — {g12_client} simulation output is clean.", err=True)

        except FileNotFoundError as exc:
            click.echo(f"[G12] Market facts file not found: {exc}", err=True)
        except Exception as exc:
            click.echo(f"[G12] Grounding check error (non-blocking): {exc}", err=True)

    json_str = json.dumps(result, indent=2, default=str)
    if output:
        with open(output, "w") as f:
            f.write(json_str)
        click.echo(f"Simulation results written to {output}")
    else:
        click.echo(json_str)

    if calibrate:
        from src.calibration.engine import CalibrationEngine
        from src.persistence.envelope_store import load_envelope, save_envelope
        # Load the saved cohort, run benchmark calibration, save back
        click.echo(f"\n[Calibration] To calibrate, run:")
        click.echo(f"  simulatte calibrate --cohort-path {cohort} --benchmark-conversion {benchmark_conversion} --benchmark-wtp-median {benchmark_wtp_median}")


def _parse_consistency_score(notes: str | None) -> float | None:
    """Safely extract consistency_score from CalibrationState.notes string."""
    if not notes:
        return None
    try:
        for part in notes.split(";"):
            part = part.strip()
            if part.startswith("consistency_score="):
                return float(part.split("=", 1)[1])
    except (ValueError, IndexError):
        pass
    return None


async def _run_simulation(cohort_path: str, scenario_data: dict, rounds: int, tier: str = "deep",
                          social_level: str = "isolated", social_topology: str = "random_encounter") -> dict:
    import asyncio
    import uuid as _uuid
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

    social_trace_dict: dict | None = None

    if social_level != "isolated":
        # ── Social simulation path — peer influence active ────────────────────
        from src.social.loop_orchestrator import run_social_loop
        from src.social.network_builder import build_full_mesh, build_random_encounter
        from src.social.schema import SocialNetwork, NetworkTopology, SocialSimulationLevel
        import anthropic as _anthropic
        from src.utils.llm_router import get_llm_client

        click.echo(
            f"  Social mode: level={social_level}, topology={social_topology}",
            err=True,
        )

        level = SocialSimulationLevel(social_level.lower())
        personas = envelope.personas

        if social_topology == "full_mesh":
            edges = build_full_mesh(personas)
            topology = NetworkTopology.FULL_MESH
        else:
            edges = build_random_encounter(personas)
            topology = NetworkTopology.RANDOM_ENCOUNTER

        network = SocialNetwork(topology=topology, edges=edges)

        _llm_base = _anthropic.AsyncAnthropic()
        _icp_spec = getattr(envelope, 'icp_spec', None)
        sarvam_enabled = getattr(_icp_spec, 'sarvam_enabled', False) if _icp_spec else False
        _llm_client = get_llm_client(_llm_base, sarvam_enabled=sarvam_enabled)

        session_id = f"social-{_uuid.uuid4().hex[:8]}"
        decision_scenarios = [decision_scenario] * len(all_stimuli) if decision_scenario else None

        final_personas, trace, per_persona_turns = await run_social_loop(
            personas=personas,
            stimuli=all_stimuli,
            network=network,
            level=level,
            session_id=session_id,
            cohort_id=envelope.cohort_id,
            decision_scenarios=decision_scenarios,
            llm_client=_llm_client,
            tier=_tier,
        )

        results = [
            {
                "persona_id": p.persona_id,
                "persona_name": p.demographic_anchor.name,
                "rounds": per_persona_turns.get(p.persona_id, []),
            }
            for p in final_personas
        ]

        social_trace_dict = {
            "events_count": len(trace.events),
            "validity_gates": trace.validity_gate_results,
            "influence_vectors": {
                pid: {
                    "events_transmitted": iv.events_transmitted,
                    "events_received": iv.events_received,
                    "mean_gated_importance": iv.mean_gated_importance,
                }
                for pid, iv in (trace.influence_vectors or {}).items()
            },
        }

        for p in final_personas:
            click.echo(f"    Done (social): {p.persona_id}", err=True)

    else:
        # ── Standard isolated simulation path ─────────────────────────────────
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
                    round_data["response"] = loop_result.observation.content
                    round_data["decision"] = loop_result.decision.decision
                    round_data["confidence"] = loop_result.decision.confidence
                    round_data["reasoning"] = loop_result.decision.reasoning_trace
                persona_results["rounds"].append(round_data)
            click.echo(f"    Done: {persona.persona_id}", err=True)
            return persona_results

        results = list(await asyncio.gather(*[_simulate_persona(p) for p in envelope.personas]))

    # Apply calibration
    from src.cohort.calibrator import compute_calibration_state
    calibration = compute_calibration_state(envelope, results)

    social_info: dict = {
        "social_level": social_level,
        "social_topology": social_topology if social_level != "isolated" else None,
    }
    if social_trace_dict is not None:
        social_info["trace"] = social_trace_dict

    return {
        "simulation_id": f"sim-{_uuid.uuid4().hex[:8]}",
        "cohort_id": envelope.cohort_id,
        "rounds": rounds,
        "decision_scenario": decision_scenario,
        "results": results,
        "calibration_state": {
            "status": calibration.status,
            "method_applied": calibration.method_applied,
            "consistency_score": _parse_consistency_score(calibration.notes),
            "N": len(results),
        },
        "social_simulation": social_info,
    }


cli.add_command(simulate)


# ---------------------------------------------------------------------------
# calibrate — Benchmark Calibration
# ---------------------------------------------------------------------------

@cli.command("calibrate")
@click.option("--cohort-path", required=True, type=click.Path(exists=True))
@click.option("--benchmark-conversion", type=float, default=None)
@click.option("--benchmark-wtp-median", type=float, default=None)
def calibrate_cohort(cohort_path, benchmark_conversion, benchmark_wtp_median):
    """Run benchmark calibration on a saved cohort."""
    from src.calibration.engine import CalibrationEngine
    from src.persistence.envelope_store import load_envelope, save_envelope
    from src.calibration.population_validator import validate_calibration
    import pathlib

    cohort = load_envelope(pathlib.Path(cohort_path))
    benchmarks = {}
    if benchmark_conversion:
        benchmarks["conversion_rate"] = benchmark_conversion
    if benchmark_wtp_median:
        benchmarks["wtp_median"] = benchmark_wtp_median

    if not benchmarks:
        click.echo("Error: provide at least --benchmark-conversion or --benchmark-wtp-median")
        return

    engine = CalibrationEngine()
    calibrated = engine.run_benchmark_calibration(cohort, benchmarks)

    gate_report = validate_calibration(calibrated, benchmark_conversion=benchmark_conversion)
    click.echo(gate_report.summary())

    save_envelope(calibrated, pathlib.Path(cohort_path))
    click.echo(f"[Calibration] Saved calibrated cohort to {cohort_path}")


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


# ---------------------------------------------------------------------------
# onboard command — Sprint 27
# ---------------------------------------------------------------------------

@click.command("onboard")
@click.option("--data-file", required=True, type=click.Path(exists=True),
              help="Path to client data file (CSV, JSON array, JSON lines, or plain text).")
@click.option("--icp-spec", default=None, type=click.Path(exists=True),
              help="Path to ICP spec JSON file (optional — used for collision detection).")
@click.option("--output", default=None, help="Output JSON file for IngestionResult (default: stdout).")
@click.option("--tag", is_flag=True, default=False,
              help="Run Haiku signal tagging (requires Anthropic API key).")
def onboard(data_file, icp_spec, output, tag):
    """Ingest a client data file: detect format, redact PII, validate, optionally tag signals."""
    import json
    from pathlib import Path
    from src.onboarding.ingestion import ingest

    raw_bytes = Path(data_file).read_bytes()
    result = ingest(raw_bytes, run_tagger=tag)

    out = {
        "format_detected": result.format_detected,
        "n_raw_signals": len(result.raw_signals),
        "n_redacted_signals": len(result.redacted_signals),
        "redaction_log": result.redaction_log.summary() if result.redaction_log else None,
        "validation": result.validation_report.summary() if result.validation_report else None,
        "ready_for_grounding": result.ready_for_grounding,
    }
    if result.tagged_corpus is not None:
        out["tag_distribution"] = result.tagged_corpus.tag_distribution
        out["n_decision_signals"] = result.tagged_corpus.n_decision_signals

    text = json.dumps(out, indent=2)
    if output:
        Path(output).write_text(text, encoding="utf-8")
        click.echo(f"Ingestion result written to {output}")
    else:
        click.echo(text)


cli.add_command(onboard)


# ---------------------------------------------------------------------------
# language-readiness — O15 Language Readiness Report (Sprint 29)
# ---------------------------------------------------------------------------

@cli.command("language-readiness")
@click.option("--language", required=True, help="Language to check (e.g. hindi, tamil).")
def language_readiness(language):
    """Show language readiness report for a given language (O15 framework)."""
    import json
    from src.validation.language_gates import check_cr1_v, check_cr2_v, check_cr3_v, check_cr4_v
    from src.validation.readiness_report import build_readiness_report

    cr1 = check_cr1_v(language)
    cr2 = check_cr2_v(language)
    cr3 = check_cr3_v(language)
    cr4 = check_cr4_v(language)
    report = build_readiness_report(language, cr1, cr2, cr3, cr4)

    out = {
        "language": report.language,
        "status": report.status,
        "gates": {
            "CR1-V": report.cr1_v_status,
            "CR2-V": report.cr2_v_status,
            "CR3-V": report.cr3_v_status,
            "CR4-V": report.cr4_v_status,
        },
        "tech_lead_sign_off_required": report.tech_lead_sign_off_required,
        "blocking_reasons": report.blocking_reasons,
    }
    click.echo(json.dumps(out, indent=2))


cli.add_command(language_readiness)


# ---------------------------------------------------------------------------
# registry — Persona Registry CLI (Sprint 30)
# ---------------------------------------------------------------------------

@click.group()
def registry():
    """Persona registry operations."""
    pass


@registry.command("get")
@click.option("--id", "persona_id", required=True, help="Persona ID to retrieve.")
@click.option("--registry-path", default=None, help="Registry root path (default: data/registry).")
def registry_get(persona_id, registry_path):
    """Retrieve a persona from the registry by ID and print as JSON."""
    import json
    from src.registry.persona_registry import PersonaRegistry
    reg = PersonaRegistry(registry_path)
    persona = reg.get(persona_id)
    if persona is None:
        click.echo(json.dumps({"error": f"Persona '{persona_id}' not found in registry."}))
        raise SystemExit(1)
    click.echo(persona.model_dump_json(indent=2))


@registry.command("find")
@click.option("--age-min", type=int, default=None)
@click.option("--age-max", type=int, default=None)
@click.option("--gender", default=None)
@click.option("--city-tier", default=None)
@click.option("--domain", default=None)
@click.option("--registry-path", default=None)
def registry_find(age_min, age_max, gender, city_tier, domain, registry_path):
    """Find personas matching demographic criteria."""
    import json
    from src.registry.persona_registry import PersonaRegistry
    from dataclasses import asdict
    reg = PersonaRegistry(registry_path)
    results = reg.find(age_min=age_min, age_max=age_max, gender=gender, city_tier=city_tier, domain=domain)
    click.echo(json.dumps([asdict(r) for r in results], indent=2))


@registry.command("export")
@click.option("--cohort-id", required=True)
@click.option("--output", required=True, help="Output directory path.")
@click.option("--registry-path", default=None)
def registry_export(cohort_id, output, registry_path):
    """Export all personas from the registry to an output directory as JSON files."""
    import json
    import pathlib
    from src.registry.persona_registry import PersonaRegistry
    reg = PersonaRegistry(registry_path)
    entries = reg.list_all()
    out_dir = pathlib.Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        persona = reg.get(entry.persona_id)
        if persona:
            (out_dir / f"{entry.persona_id}.json").write_text(persona.model_dump_json(indent=2))
    click.echo(json.dumps({"exported": len(entries), "cohort_id": cohort_id, "output": str(out_dir)}))


@registry.command("sync")
@click.option("--cohort-path", required=True, help="Path to JSON file with list of PersonaRecord dicts.")
@click.option("--registry-path", default=None)
def registry_sync(cohort_path, registry_path):
    """Import personas from a JSON file into the registry."""
    import json
    from src.registry.persona_registry import PersonaRegistry
    from dataclasses import asdict
    reg = PersonaRegistry(registry_path)
    entries = reg.sync_from_json(cohort_path)
    click.echo(json.dumps({"synced": len(entries), "persona_ids": [e.persona_id for e in entries]}))


cli.add_command(registry)


# ---------------------------------------------------------------------------
# grounding-check — Standalone G12 gate (run on any saved simulation output)
# ---------------------------------------------------------------------------

@cli.command("grounding-check")
@click.option("--simulation-output", required=True, type=click.Path(exists=True),
              help="Path to a saved simulation output JSON (from simulatte simulate --output).")
@click.option("--client", default=None,
              help="Client name for market facts (e.g. lumio, lo_foods, littlejoys). Auto-resolved from simulation output if omitted.")
@click.option("--product-frame", default=None,
              help="Product frame text or path to a .txt file. If omitted, stimuli from the simulation output are used.")
@click.option("--output", default=None,
              help="Write G12 report to this JSON file (default: print to stdout).")
def grounding_check_cmd(simulation_output, client, product_frame, output):
    """Run the G12 Simulation Grounding Check on a saved simulation output.

    \b
    Example — check a Lumio simulation:
      simulatte grounding-check \\
        --simulation-output sim_results.json \\
        --client lumio

    \b
    Example — check with explicit product frame text file:
      simulatte grounding-check \\
        --simulation-output sim_results.json \\
        --client lo_foods \\
        --product-frame product_brief.txt \\
        --output g12_report.json
    """
    import json
    import pathlib
    from src.validation.grounding_check import run_grounding_check, load_market_facts

    # Load simulation output
    sim_data = json.loads(pathlib.Path(simulation_output).read_text(encoding="utf-8"))

    # Resolve product frame
    if product_frame:
        pf_path = pathlib.Path(product_frame)
        if pf_path.exists():
            frame_text = pf_path.read_text(encoding="utf-8")
        else:
            frame_text = product_frame  # treat as inline text
    else:
        # Fall back to stimuli embedded in the simulation output
        stimuli = []
        for r in sim_data.get("results", []):
            for rnd in r.get("rounds", []):
                s = rnd.get("stimulus")
                if s:
                    stimuli.append(str(s))
        decision = sim_data.get("decision_scenario")
        if decision:
            stimuli.append(str(decision))
        frame_text = " ".join(dict.fromkeys(stimuli))  # deduplicated, order-preserved

    # Resolve client — explicit flag wins; fall back to what's embedded in the sim output
    resolved_client = client or sim_data.get("grounding_check", {}).get("client", "")
    if not resolved_client:
        click.echo(
            "[G12] Error: --client is required (or run simulatte simulate first so the "
            "client is embedded in the output automatically).",
            err=True,
        )
        raise SystemExit(1)

    # Load market facts
    try:
        market_facts = load_market_facts(resolved_client)
    except FileNotFoundError as exc:
        click.echo(f"[G12] Error: {exc}", err=True)
        raise SystemExit(1)

    # Build persona_outputs from simulation results
    persona_outputs = []
    for r in sim_data.get("results", []):
        pid = r.get("persona_id")
        persona_dict = {"persona_id": pid}
        quotes = []
        for rnd in r.get("rounds", []):
            if rnd.get("response"):
                quotes.append(rnd["response"])
            if rnd.get("reasoning"):
                quotes.append(rnd["reasoning"])
        if quotes:
            persona_dict["quotes"] = quotes
        persona_outputs.append(persona_dict)

    # Run G12
    report = run_grounding_check(
        product_frame=frame_text,
        market_facts=market_facts,
        persona_outputs=persona_outputs,
    )

    click.echo(report.summary())

    result = {
        "passed": report.passed,
        "issue_count": len(report.issues),
        "clean_count": report.clean_count,
        "issues": [
            {
                "type": i.issue_type,
                "severity": i.severity,
                "persona_id": i.persona_id,
                "location": i.location,
                "contaminated_text": i.contaminated_text,
                "reason": i.reason,
                "suggested_fix": i.suggested_fix,
            }
            for i in report.issues
        ],
    }

    json_str = json.dumps(result, indent=2, default=str)
    if output:
        pathlib.Path(output).write_text(json_str, encoding="utf-8")
        click.echo(f"[G12] Report written to {output}")
    else:
        click.echo(json_str)

    if not report.passed:
        raise SystemExit(1)  # non-zero exit so CI pipelines can catch it


if __name__ == "__main__":
    cli()
