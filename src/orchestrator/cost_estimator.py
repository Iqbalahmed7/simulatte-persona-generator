"""
CostEstimator — pre-run cost and time projection for persona generation.

Computes a line-item breakdown before a single API call is made, allowing
callers to confirm before proceeding.  All pricing uses Anthropic list rates;
override via ANTHROPIC_SONNET_PRICE_IN / _OUT / HAIKU_PRICE_IN / _OUT env vars.

Usage::

    from src.orchestrator.cost_estimator import CostEstimator
    from src.orchestrator.brief import PersonaGenerationBrief

    brief = PersonaGenerationBrief(client="Acme", domain="cpg",
                                   business_problem="...", count=50)
    est = CostEstimator(brief, tier="deep")
    print(est.formatted_estimate())
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

TierLiteral = Literal["deep", "signal", "volume"]


# ── Anthropic pricing ($ per 1M tokens) ──────────────────────────────────────
# Override via environment variables for updated pricing.
def _price(env_key: str, default: float) -> float:
    return float(os.getenv(env_key, str(default)))


SONNET_IN  = _price("ANTHROPIC_SONNET_PRICE_IN",  3.00)
SONNET_OUT = _price("ANTHROPIC_SONNET_PRICE_OUT", 15.00)
HAIKU_IN   = _price("ANTHROPIC_HAIKU_PRICE_IN",   0.80)
HAIKU_OUT  = _price("ANTHROPIC_HAIKU_PRICE_OUT",  4.00)

# ── Token budgets per phase (conservative estimates from benchmark data) ───────

# Generation phase — per persona (always Sonnet)
GEN_INPUT_TOKENS_PER_PERSONA  = 14_200   # attribute fills + life story + narrative
GEN_OUTPUT_TOKENS_PER_PERSONA = 4_868

# Pre-generation phase — fixed per project
SIGNAL_TAG_INPUT_TOKENS  = 11_700   # 10 batches × 1,170 tokens (500 docs)
SIGNAL_TAG_OUTPUT_TOKENS = 4_000
DOMAIN_EXT_INPUT_TOKENS  = 1_700
DOMAIN_EXT_OUTPUT_TOKENS = 2_000

# Simulation phase — per persona per stimulus
# DEEP:   Haiku perceive + Sonnet reflect (conditional) + Sonnet decide (conditional)
# SIGNAL: Haiku perceive + Haiku reflect + Sonnet decide
# VOLUME: Haiku perceive + Haiku reflect + Haiku decide

_SIM_PER_STIMULUS = {
    "deep": {
        "perceive_in": 600, "perceive_out": 200,       # Haiku
        "reflect_in": 1_200, "reflect_out": 400,        # Sonnet (fires ~60% of turns)
        "decide_in": 900, "decide_out": 350,            # Sonnet (if decision_scenario)
        "reflect_rate": 0.60,
        "decide_rate": 1.0,   # assumes decision_scenario always provided
    },
    "signal": {
        "perceive_in": 600, "perceive_out": 200,       # Haiku
        "reflect_in": 1_200, "reflect_out": 400,        # Haiku
        "decide_in": 900, "decide_out": 350,            # Sonnet
        "reflect_rate": 0.60,
        "decide_rate": 1.0,
    },
    "volume": {
        "perceive_in": 600, "perceive_out": 200,       # Haiku
        "reflect_in": 1_200, "reflect_out": 400,        # Haiku
        "decide_in": 900, "decide_out": 350,            # Haiku
        "reflect_rate": 0.60,
        "decide_rate": 1.0,
    },
}

# Time estimates (seconds) — based on benchmark: 20 personas / 5 stimuli ≈ 18 min
# Generation dominates; simulation adds ~30–50% on top.
_TIME_GENERATION_BASE = 8 * 60       # 8 min baseline for first 10 personas
_TIME_GENERATION_PER_10 = 5 * 60     # +5 min per additional 10 personas
_TIME_SIM_PER_STIMULUS_PER_100 = 3 * 60  # 3 min per stimulus per 100 personas (parallel)


@dataclass
class CostLine:
    label: str
    cost: float
    notes: str = ""


@dataclass
class CostEstimate:
    tier: TierLiteral
    count: int
    n_stimuli: int
    has_decision_scenario: bool
    has_corpus: bool

    pre_gen_lines: list[CostLine] = field(default_factory=list)
    gen_lines: list[CostLine] = field(default_factory=list)
    sim_lines: list[CostLine] = field(default_factory=list)

    est_seconds_min: int = 0
    est_seconds_max: int = 0

    @property
    def pre_gen_total(self) -> float:
        return sum(l.cost for l in self.pre_gen_lines)

    @property
    def gen_total(self) -> float:
        return sum(l.cost for l in self.gen_lines)

    @property
    def sim_total(self) -> float:
        return sum(l.cost for l in self.sim_lines)

    @property
    def total(self) -> float:
        return self.pre_gen_total + self.gen_total + self.sim_total

    @property
    def per_persona(self) -> float:
        return self.total / max(self.count, 1)

    @property
    def est_time_range(self) -> str:
        lo = self.est_seconds_min // 60
        hi = self.est_seconds_max // 60
        if lo == hi:
            return f"~{lo} min"
        return f"~{lo}–{hi} min"


def _token_cost(input_tokens: int, output_tokens: int,
                model: Literal["sonnet", "haiku"]) -> float:
    if model == "sonnet":
        return (input_tokens * SONNET_IN + output_tokens * SONNET_OUT) / 1_000_000
    return (input_tokens * HAIKU_IN + output_tokens * HAIKU_OUT) / 1_000_000


class CostEstimator:
    """Computes a full pre-run cost estimate for a PersonaGenerationBrief."""

    def __init__(
        self,
        count: int,
        tier: TierLiteral,
        n_stimuli: int = 0,
        has_decision_scenario: bool = False,
        has_corpus: bool = False,
        run_domain_extraction: bool = False,
    ) -> None:
        self.count = count
        self.tier = tier
        self.n_stimuli = n_stimuli
        self.has_decision_scenario = has_decision_scenario
        self.has_corpus = has_corpus
        self.run_domain_extraction = run_domain_extraction
        self._estimate: CostEstimate | None = None

    # ── Public API ────────────────────────────────────────────────────────

    def compute(self) -> CostEstimate:
        if self._estimate is not None:
            return self._estimate

        est = CostEstimate(
            tier=self.tier,
            count=self.count,
            n_stimuli=self.n_stimuli,
            has_decision_scenario=self.has_decision_scenario,
            has_corpus=self.has_corpus,
        )

        # 1 — Pre-generation (fixed per project)
        if self.has_corpus:
            cost = _token_cost(SIGNAL_TAG_INPUT_TOKENS, SIGNAL_TAG_OUTPUT_TOKENS, "haiku")
            est.pre_gen_lines.append(CostLine(
                label="Signal tagging (~500 docs)",
                cost=cost,
                notes="Haiku · one-time per project",
            ))
        if self.run_domain_extraction:
            cost = _token_cost(DOMAIN_EXT_INPUT_TOKENS, DOMAIN_EXT_OUTPUT_TOKENS, "sonnet")
            est.pre_gen_lines.append(CostLine(
                label="Domain taxonomy extraction",
                cost=cost,
                notes="Sonnet · one-time per project",
            ))

        # 2 — Generation (per persona, always Sonnet)
        gen_cost = _token_cost(
            GEN_INPUT_TOKENS_PER_PERSONA * self.count,
            GEN_OUTPUT_TOKENS_PER_PERSONA * self.count,
            "sonnet",
        )
        est.gen_lines.append(CostLine(
            label=f"Persona generation ({self.count} × Sonnet)",
            cost=gen_cost,
            notes=f"~26–28 calls per persona · {self.count} personas",
        ))

        # 3 — Simulation (per persona per stimulus, tier-dependent)
        if self.n_stimuli > 0:
            sim_cost = self._compute_sim_cost()
            est.sim_lines.append(CostLine(
                label=f"Simulation — {self.tier.upper()} ({self.n_stimuli} stimuli × {self.count} personas)",
                cost=sim_cost,
                notes=self._sim_model_notes(),
            ))

        # 4 — Time estimates
        est.est_seconds_min, est.est_seconds_max = self._time_estimate()

        self._estimate = est
        return est

    def formatted_estimate(
        self,
        brief_label: str = "",
        tier_recommendation_reason: str = "",
        alt_tier: str | None = None,
        alt_saving: float | None = None,
    ) -> str:
        """Returns a formatted console string for pre-run confirmation."""
        est = self.compute()
        lines: list[str] = []

        w = 58  # box width

        def box_line(text: str = "", fill: str = " ") -> str:
            return f"║  {text:<{w - 4}}║"

        lines.append("╔" + "═" * (w - 2) + "╗")
        lines.append(box_line("SIMULATTE PERSONA GENERATOR — COST ESTIMATE"))
        lines.append("╠" + "═" * (w - 2) + "╣")

        if brief_label:
            lines.append(box_line(f"Brief:   {brief_label}"))
        lines.append(box_line(f"Count:   {self.count} personas"))
        lines.append(box_line(f"Intent:  → Tier: {self.tier.upper()}"))
        if tier_recommendation_reason:
            lines.append(box_line(f"         {tier_recommendation_reason}"))
        lines.append("╠" + "═" * (w - 2) + "╣")

        # Cost lines
        if est.pre_gen_lines:
            for line in est.pre_gen_lines:
                lines.append(box_line(f"  {line.label:<40}  ${line.cost:>6.2f}"))
        for line in est.gen_lines:
            lines.append(box_line(f"  {line.label:<40}  ${line.cost:>6.2f}"))
        for line in est.sim_lines:
            lines.append(box_line(f"  {line.label:<40}  ${line.cost:>6.2f}"))

        lines.append(box_line("─" * (w - 4)))
        lines.append(box_line(f"  {'TOTAL ESTIMATE':<40}  ${est.total:>6.2f}"))
        lines.append(box_line(f"  {'Per persona':<40}  ${est.per_persona:>6.3f}"))
        lines.append(box_line(f"  {'Estimated time':<40}  {est.est_time_range}"))

        if alt_tier and alt_saving:
            lines.append("╠" + "═" * (w - 2) + "╣")
            lines.append(box_line(f"  Alt: switch to {alt_tier.upper()} to save ~${alt_saving:.2f}"))

        lines.append("╚" + "═" * (w - 2) + "╝")
        return "\n".join(lines)

    # ── Private helpers ───────────────────────────────────────────────────

    def _compute_sim_cost(self) -> float:
        spec = _SIM_PER_STIMULUS[self.tier]
        total = 0.0
        for _ in range(self.n_stimuli):
            # Perceive — always Haiku
            total += _token_cost(spec["perceive_in"], spec["perceive_out"], "haiku") * self.count

            # Reflect — conditional, model depends on tier
            reflect_model: Literal["sonnet", "haiku"] = (
                "sonnet" if self.tier == "deep" else "haiku"
            )
            total += (
                _token_cost(spec["reflect_in"], spec["reflect_out"], reflect_model)
                * self.count
                * spec["reflect_rate"]
            )

            # Decide — if decision_scenario present
            if self.has_decision_scenario:
                decide_model: Literal["sonnet", "haiku"] = (
                    "haiku" if self.tier == "volume" else "sonnet"
                )
                total += (
                    _token_cost(spec["decide_in"], spec["decide_out"], decide_model)
                    * self.count
                    * spec["decide_rate"]
                )

        return total

    def _sim_model_notes(self) -> str:
        if self.tier == "deep":
            return "Haiku perceive · Sonnet reflect · Sonnet decide"
        if self.tier == "signal":
            return "Haiku perceive · Haiku reflect · Sonnet decide"
        return "Haiku perceive · Haiku reflect · Haiku decide"

    def _time_estimate(self) -> tuple[int, int]:
        """Returns (min_seconds, max_seconds) for the full run."""
        # Generation time — sub-linear due to async parallelism
        n = self.count
        if n <= 10:
            gen_min, gen_max = 8 * 60, 12 * 60
        elif n <= 30:
            gen_min, gen_max = 15 * 60, 25 * 60
        elif n <= 50:
            gen_min, gen_max = 25 * 60, 40 * 60
        else:
            gen_min, gen_max = 45 * 60, 75 * 60

        # Simulation time — adds ~3 min per stimulus per 100 personas (parallel)
        sim_min = sim_max = 0
        if self.n_stimuli > 0:
            per_stim_per_100 = _TIME_SIM_PER_STIMULUS_PER_100
            factor = max(n / 100, 0.1)
            sim_min = int(self.n_stimuli * per_stim_per_100 * factor * 0.7)
            sim_max = int(self.n_stimuli * per_stim_per_100 * factor * 1.3)

        return gen_min + sim_min, gen_max + sim_max
