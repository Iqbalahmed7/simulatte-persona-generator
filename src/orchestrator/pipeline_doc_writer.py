"""
PipelineDocWriter — auto-generates a structured pipeline note after generation.

Writes a Markdown document capturing:
  - Brief (client, domain, intent, count)
  - Tier used + model routing
  - Cost breakdown (estimated vs actual)
  - Quality gate results (G1–G12)
  - Persona summary (demographics, decision styles, grounding state)
  - Simulation summary (if applicable)
  - Timestamp + run ID

The output is saved to output_dir/{client}_{date}_{run_id}.md.

Usage::

    from src.orchestrator.pipeline_doc_writer import PipelineDocWriter

    writer = PipelineDocWriter(result, brief, estimate)
    path = writer.write(output_dir="./pipeline_docs")
    print(f"Pipeline doc written to: {path}")
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.orchestrator.brief import PersonaGenerationBrief
    from src.orchestrator.cost_estimator import CostEstimate
    from src.orchestrator.result import PersonaGenerationResult


class PipelineDocWriter:

    def __init__(
        self,
        result: "PersonaGenerationResult",
        brief: "PersonaGenerationBrief",
        estimate: "CostEstimate",
    ) -> None:
        self.result = result
        self.brief = brief
        self.estimate = estimate

    def write(self, output_dir: str | Path = ".") -> Path:
        """Generate the pipeline doc and write it to output_dir.  Returns path."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        safe_client = (
            self.brief.client.replace(" ", "_").replace("/", "-").replace("\\", "-").lower()
        )
        filename = f"{safe_client}_{date_str}_{self.result.run_id[-8:]}.md"
        path = out_dir / filename

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._render())
        return path

    def _render(self) -> str:
        r = self.result
        b = self.brief
        e = self.estimate
        qr = r.quality_report
        ca = r.cost_actual

        lines: list[str] = []

        def h1(text: str) -> None:
            lines.append(f"# {text}\n")

        def h2(text: str) -> None:
            lines.append(f"\n## {text}\n")

        def h3(text: str) -> None:
            lines.append(f"\n### {text}\n")

        def row(label: str, value: str) -> None:
            lines.append(f"| {label} | {value} |")

        def hr() -> None:
            lines.append("\n---\n")

        # ── Header ────────────────────────────────────────────────────────
        h1(f"Simulatte Pipeline Note — {b.client}")
        lines.append(f"**Run ID:** `{r.run_id}`  ")
        lines.append(f"**Generated:** {r.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ")
        lines.append(f"**Status:** {'✅ All gates passed' if qr.all_passed else '⚠️ Review required'}  ")

        # ── Brief ─────────────────────────────────────────────────────────
        h2("Brief")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        row("Client", b.client)
        row("Domain", b.domain)
        row("Business Problem", b.business_problem)
        row("Count", str(b.count))
        row("Run Intent", b.run_intent.value)
        row("Mode", b.mode)
        row("Sarvam Enabled", str(b.sarvam_enabled))
        if b.anchor_overrides:
            row("Anchor Overrides", str(b.anchor_overrides))
        if b.corpus_path:
            row("Corpus Path", str(b.corpus_path))

        # ── Tier & Model Routing ──────────────────────────────────────────
        h2("Tier & Model Routing")
        lines.append("| Stage | Model |")
        lines.append("|---|---|")
        row("Tier Used", r.tier_used.upper())
        row("Generation (all tiers)", "claude-sonnet-4-6")
        if r.tier_used == "deep":
            row("Perceive", "claude-haiku-4-5-20251001")
            row("Reflect", "claude-sonnet-4-6")
            row("Decide", "claude-sonnet-4-6")
        elif r.tier_used == "signal":
            row("Perceive", "claude-haiku-4-5-20251001")
            row("Reflect", "claude-haiku-4-5-20251001")
            row("Decide", "claude-sonnet-4-6")
        else:
            row("Perceive", "claude-haiku-4-5-20251001")
            row("Reflect", "claude-haiku-4-5-20251001")
            row("Decide", "claude-haiku-4-5-20251001")

        # ── Cost ──────────────────────────────────────────────────────────
        h2("Cost Breakdown")
        lines.append("| Phase | Estimated | Actual |")
        lines.append("|---|---|---|")
        lines.append(f"| Pre-generation | ${e.pre_gen_total:.2f} | ${ca.pre_generation:.2f} |")
        lines.append(f"| Generation | ${e.gen_total:.2f} | ${ca.generation:.2f} |")
        lines.append(f"| Simulation | ${e.sim_total:.2f} | ${ca.simulation:.2f} |")
        lines.append(f"| **Total** | **${e.total:.2f}** | **${ca.total:.2f}** |")
        lines.append(f"| Per Persona | ${e.total/max(b.count,1):.3f} | ${r.cost_per_persona:.3f} |")

        if r.wall_clock_seconds:
            lines.append(f"\n**Wall-clock time:** {r.wall_clock_seconds/60:.1f} min")

        # ── Quality Gates ─────────────────────────────────────────────────
        h2("Quality Gates")
        lines.append("| Gate | Result |")
        lines.append("|---|---|")
        for g in qr.gates_passed:
            lines.append(f"| {g} | ✅ Passed |")
        for g in qr.gates_failed:
            lines.append(f"| {g} | ❌ Failed |")

        lines.append(f"\n**Personas quarantined:** {qr.personas_quarantined}")
        lines.append(f"**Personas regenerated:** {qr.personas_regenerated}")
        lines.append(f"**Distinctiveness score:** {qr.distinctiveness_score or 'N/A'}")
        lines.append(f"**Grounding state:** {qr.grounding_state}")

        if qr.contamination_findings:
            h3("Contamination Findings (G12)")
            for f in qr.contamination_findings:
                lines.append(f"- `{f.get('persona_id')}`: {f.get('type')} — {f.get('detail')}")

        # ── Persona Summary ───────────────────────────────────────────────
        h2("Cohort Summary")
        cs = r.cohort_envelope.get("cohort_summary", {})
        if cs:
            dsd = cs.get("decision_style_distribution", {})
            if dsd:
                h3("Decision Style Distribution")
                lines.append("| Style | Share |")
                lines.append("|---|---|")
                for style, share in dsd.items():
                    lines.append(f"| {style} | {share:.0%} |")

            tad = cs.get("trust_anchor_distribution", {})
            if tad:
                h3("Trust Anchor Distribution")
                lines.append("| Anchor | Share |")
                lines.append("|---|---|")
                for anchor, share in tad.items():
                    lines.append(f"| {anchor} | {share:.0%} |")

        # ── Persona Index ─────────────────────────────────────────────────
        h2(f"Persona Index ({r.count_delivered} personas)")
        lines.append("| ID | Name | Age | Location | Decision Style |")
        lines.append("|---|---|---|---|---|")
        for p in r.personas[:50]:  # cap at 50 for readability
            da = p.get("demographic_anchor", {})
            di = p.get("derived_insights", {})
            lines.append(
                f"| `{p.get('persona_id','')}` "
                f"| {da.get('name','')} "
                f"| {da.get('age','')} "
                f"| {da.get('location','')} "
                f"| {di.get('decision_style','')} |"
            )
        if r.count_delivered > 50:
            lines.append(f"\n*… and {r.count_delivered - 50} more personas*")

        # ── Simulation Summary ────────────────────────────────────────────
        if r.simulation_results:
            h2("Simulation Summary")
            sim = r.simulation_results
            lines.append(f"**Simulation ID:** `{sim.get('simulation_id', 'N/A')}`  ")
            lines.append(f"**Decision scenario:** {sim.get('decision_scenario', 'None')}  ")
            lines.append(f"**Rounds:** {sim.get('rounds', 1)}  ")

            results = sim.get("results", [])
            decided = [
                r for r in results
                if any(
                    turn.get("decided")
                    for rnd in r.get("rounds", [])
                    for turn in ([rnd] if isinstance(rnd, dict) else [])
                )
            ]
            lines.append(f"**Personas that reached a decision:** {len(decided)} / {len(results)}")

        # ── Cohort file path ──────────────────────────────────────────────
        if r.cohort_file_path:
            hr()
            lines.append(f"**Cohort file:** `{r.cohort_file_path}`")

        lines.append(f"\n---\n*Generated by Simulatte Persona Orchestrator · {r.run_id}*")

        return "\n".join(lines) + "\n"
