"""
TierAdvisor — maps RunIntent → recommended simulation tier, with reasoning.

Rules (in priority order):
  1. If tier_override is set on the brief → use it unconditionally.
  2. DELIVER intent   → DEEP
  3. EXPLORE intent   → SIGNAL
  4. CALIBRATE intent → SIGNAL
  5. VOLUME intent    → VOLUME
  6. If count > 200   → nudge toward VOLUME regardless of intent (cost safety)
  7. Default fallback → SIGNAL

Usage::

    from src.orchestrator.tier_advisor import TierAdvisor
    from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

    brief = PersonaGenerationBrief(
        client="Acme", domain="cpg",
        business_problem="...", count=50,
        run_intent=RunIntent.DELIVER,
    )
    advice = TierAdvisor.advise(brief)
    print(advice.tier)          # "deep"
    print(advice.reason)        # "run_intent=deliver → final client output"
    print(advice.alt_tier)      # "signal"
    print(advice.alt_saving_pct)# 47
"""

from __future__ import annotations

from dataclasses import dataclass

from src.orchestrator.brief import PersonaGenerationBrief, RunIntent


@dataclass
class TierAdvice:
    tier: str                     # "deep" | "signal" | "volume"
    reason: str                   # Human-readable explanation
    alt_tier: str | None          # Cheaper alternative (if applicable)
    alt_saving_pct: int | None    # % cost saving vs recommended tier
    forced: bool = False          # True if tier_override was set


# Relative simulation cost per tier (DEEP = 100%)
_TIER_SIM_COST_PCT = {
    "deep":   100,
    "signal":  53,
    "volume":  25,
}


class TierAdvisor:
    """Stateless advisor — all logic in class methods."""

    @classmethod
    def advise(cls, brief: PersonaGenerationBrief) -> TierAdvice:
        # ── 1. Honour explicit override ──────────────────────────────────
        if brief.tier_override:
            tier = brief.tier_override.lower()
            return TierAdvice(
                tier=tier,
                reason=f"tier_override='{tier}' (manually specified)",
                alt_tier=None,
                alt_saving_pct=None,
                forced=True,
            )

        # ── 2. Large cohort safety nudge ─────────────────────────────────
        if brief.count > 200 and brief.run_intent != RunIntent.DELIVER:
            tier = "volume"
            reason = (
                f"count={brief.count} > 200 with intent={brief.run_intent.value} "
                f"→ VOLUME to manage cost"
            )
            return TierAdvice(
                tier=tier,
                reason=reason,
                alt_tier="signal",
                alt_saving_pct=None,
            )

        # ── 3. Intent mapping ─────────────────────────────────────────────
        mapping: dict[RunIntent, tuple[str, str]] = {
            RunIntent.DELIVER:   ("deep",   "run_intent=deliver → final client output"),
            RunIntent.EXPLORE:   ("signal", "run_intent=explore → hypothesis testing"),
            RunIntent.CALIBRATE: ("signal", "run_intent=calibrate → prompt / taxonomy tuning"),
            RunIntent.VOLUME:    ("volume", "run_intent=volume → large-scale distribution run"),
        }

        tier, reason = mapping.get(brief.run_intent, ("signal", "default fallback"))

        alt_tier, alt_saving_pct = cls._compute_alt(tier)

        return TierAdvice(
            tier=tier,
            reason=reason,
            alt_tier=alt_tier,
            alt_saving_pct=alt_saving_pct,
        )

    @classmethod
    def _compute_alt(cls, tier: str) -> tuple[str | None, int | None]:
        """Returns the next cheaper tier and approximate % saving vs tier."""
        if tier == "deep":
            saving = _TIER_SIM_COST_PCT["deep"] - _TIER_SIM_COST_PCT["signal"]
            return "signal", saving
        if tier == "signal":
            saving = _TIER_SIM_COST_PCT["signal"] - _TIER_SIM_COST_PCT["volume"]
            return "volume", saving
        return None, None  # volume has no cheaper option

    @classmethod
    def describe_models(cls, tier: str) -> dict[str, str]:
        """Returns the model used at each cognitive stage for a given tier."""
        _HAIKU  = "claude-haiku-4-5-20251001"
        _SONNET = "claude-sonnet-4-6"
        mapping = {
            "deep":   {"perceive": _HAIKU, "reflect": _SONNET, "decide": _SONNET},
            "signal": {"perceive": _HAIKU, "reflect": _HAIKU,  "decide": _SONNET},
            "volume": {"perceive": _HAIKU, "reflect": _HAIKU,  "decide": _HAIKU},
        }
        return mapping.get(tier, mapping["signal"])
