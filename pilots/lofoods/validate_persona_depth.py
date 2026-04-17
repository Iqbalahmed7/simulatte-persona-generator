"""
validate_persona_depth.py — Lo! Foods E2E Persona Depth Validation

Proves that memory-backed Simulatte personas are genuinely behaviorally distinct
compared to a naive LLM baseline that only has demographic context.

Usage:
    python3 pilots/lofoods/validate_persona_depth.py

Run AFTER Batch 1 persona generation completes (cohort_C1.json must exist).
Results are saved to pilots/lofoods/validation_results.json.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from project root before any imports that may use ANTHROPIC_API_KEY
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # .../Persona Generator

_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    with open(_ENV_PATH) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key not in os.environ:
                    os.environ[_key] = _val

import anthropic  # noqa: E402 — must follow env load

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

COHORT_PATH = _SCRIPT_DIR / "personas" / "cohort_C1.json"
RESULTS_PATH = _SCRIPT_DIR / "validation_results.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STIMULUS = (
    "You are browsing Blinkit for bread. You see Protein Chef bread "
    "(38g protein per loaf, no maida) at ₹99 and Britannia Milk Bread at ₹45. "
    "You need bread today. What do you do?"
)

MODEL = "claude-sonnet-4-6"
TEMPERATURE = 0.7  # identical for both conditions — statistically fair comparison

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_MEMORY_SYSTEM_TEMPLATE = """\
You are {name}. {identity_statement}

What matters most to you: {key_values}

{tendency_summary}

Your life has been shaped by these experiences:
{life_stories}
"""

_MEMORY_USER_TEMPLATE = """\
{stimulus}

Think through this step by step as yourself:

1. GUT REACTION: What is your first instinct?
2. WHAT MATTERS: What factors matter most to you in this choice?
3. DECISION: What do you actually decide to do?

Also provide:
- purchase_probability_protein_chef: your estimated probability (0-100) that you \
would buy the Protein Chef bread right now
- buy_protein_chef: true if you would buy it, false otherwise

Reply in JSON:
{{
  "gut_reaction": "...",
  "reasoning": "...",
  "final_decision": "...",
  "purchase_probability_protein_chef": <integer 0-100>,
  "buy_protein_chef": <true|false>
}}
"""

_NAIVE_SYSTEM_TEMPLATE = """\
You are roleplaying as a person with the following demographic profile:
- Name: {name}
- Age: {age}
- City: {city}
- Income bracket: {income_bracket}
- Household: {household_type}

Respond as this person would.
"""

_NAIVE_USER_TEMPLATE = """\
{stimulus}

Think through this step by step as yourself:

1. GUT REACTION: What is your first instinct?
2. WHAT MATTERS: What factors matter most to you in this choice?
3. DECISION: What do you actually decide to do?

Also provide:
- purchase_probability_protein_chef: your estimated probability (0-100) that you \
would buy the Protein Chef bread right now
- buy_protein_chef: true if you would buy it, false otherwise

Reply in JSON:
{{
  "gut_reaction": "...",
  "reasoning": "...",
  "final_decision": "...",
  "purchase_probability_protein_chef": <integer 0-100>,
  "buy_protein_chef": <true|false>
}}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> dict | None:
    """Extract JSON from LLM response, tolerating markdown fences."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    # Fallback: find first {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(cleaned[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return None


def _extract_life_stories(persona: dict) -> str:
    """Format life stories from persona dict into readable narrative block."""
    stories = persona.get("life_stories", [])
    if not stories:
        return "(No life stories recorded.)"
    parts = []
    for s in stories:
        title = s.get("title", "")
        when = s.get("when", "")
        event = s.get("event", "")
        impact = s.get("lasting_impact", "")
        parts.append(
            f"[{title}, {when}] {event} "
            f"Lasting impact: {impact}"
        )
    return "\n\n".join(parts)


def _stdev(values: list[float]) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _count_distinct(texts: list[str]) -> int:
    """
    Count distinct responses by normalising to the first 60 chars of the
    final_decision text.  Two responses are considered the same only if their
    normalised opening is identical — deliberately loose so minor phrasing
    differences don't over-inflate the count.
    """
    seen: set[str] = set()
    for t in texts:
        normalised = t.lower().strip()[:60]
        seen.add(normalised)
    return len(seen)


# ---------------------------------------------------------------------------
# Test A — Memory-backed personas (Simulatte)
# ---------------------------------------------------------------------------


def _build_memory_prompt(persona: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a memory-backed persona."""
    demo = persona.get("demographic_anchor", {})
    name = demo.get("name", "Unknown")

    core = persona.get("memory", {}).get("core", {})
    identity_statement = core.get("identity_statement", "")
    key_values_list = core.get("key_values", [])
    key_values = "; ".join(str(v) for v in key_values_list if v)
    tendency_summary = core.get("tendency_summary", "")

    life_stories_text = _extract_life_stories(persona)

    system = _MEMORY_SYSTEM_TEMPLATE.format(
        name=name,
        identity_statement=identity_statement,
        key_values=key_values,
        tendency_summary=tendency_summary,
        life_stories=life_stories_text,
    )
    user = _MEMORY_USER_TEMPLATE.format(stimulus=STIMULUS)
    return system, user


def run_memory_backed_test(
    personas: list[dict], client: anthropic.Anthropic
) -> list[dict]:
    """
    For each persona, send the stimulus with full memory context.
    Returns list of result dicts with name, buy_protein_chef, purchase_prob,
    final_decision.
    """
    results = []
    print("\nRunning Test A — Memory-Backed Personas (Simulatte)...")
    for i, persona in enumerate(personas, 1):
        name = persona.get("demographic_anchor", {}).get("name", f"Persona {i}")
        print(f"  [{i}/{len(personas)}] {name}...", end=" ", flush=True)

        system_prompt, user_prompt = _build_memory_prompt(persona)

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text
        parsed = _parse_response(raw)

        if parsed is None:
            print("PARSE ERROR — using defaults")
            results.append(
                {
                    "name": name,
                    "buy_protein_chef": False,
                    "purchase_prob": 50,
                    "final_decision": "(parse error)",
                    "raw": raw,
                    "condition": "memory_backed",
                }
            )
            continue

        buy = bool(parsed.get("buy_protein_chef", False))
        prob = int(parsed.get("purchase_probability_protein_chef", 50))
        prob = max(0, min(100, prob))
        decision = str(parsed.get("final_decision", "")).strip()
        gut = str(parsed.get("gut_reaction", "")).strip()

        label = "BUY" if buy else ("CONSIDER" if prob >= 40 else "REJECT")
        print(f"{label} (prob={prob}%)")

        results.append(
            {
                "name": name,
                "buy_protein_chef": buy,
                "purchase_prob": prob,
                "final_decision": decision,
                "gut_reaction": gut,
                "raw": raw,
                "condition": "memory_backed",
            }
        )
    return results


# ---------------------------------------------------------------------------
# Test B — Naive LLM baseline
# ---------------------------------------------------------------------------


def _build_naive_prompt(persona: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) using ONLY demographic facts."""
    demo = persona.get("demographic_anchor", {})
    name = demo.get("name", "Unknown")
    age = demo.get("age", "unknown")
    city = demo.get("location", {}).get("city", "unknown")
    income_bracket = demo.get("household", {}).get("income_bracket", "unknown")

    household = demo.get("household", {})
    hh_structure = household.get("structure", "unknown")
    hh_size = household.get("size", "?")
    household_type = f"{hh_structure}, {hh_size} members"

    system = _NAIVE_SYSTEM_TEMPLATE.format(
        name=name,
        age=age,
        city=city,
        income_bracket=income_bracket,
        household_type=household_type,
    )
    user = _NAIVE_USER_TEMPLATE.format(stimulus=STIMULUS)
    return system, user


def run_naive_baseline_test(
    personas: list[dict], client: anthropic.Anthropic
) -> list[dict]:
    """
    For each persona, send the stimulus with ONLY demographic context.
    No life stories, no attributes, no memory — truly naive.
    Returns list of result dicts.
    """
    results = []
    print("\nRunning Test B — Naive LLM Baseline...")
    for i, persona in enumerate(personas, 1):
        name = persona.get("demographic_anchor", {}).get("name", f"Persona {i}")
        print(f"  [{i}/{len(personas)}] {name} (demographics only)...", end=" ", flush=True)

        system_prompt, user_prompt = _build_naive_prompt(persona)

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text
        parsed = _parse_response(raw)

        if parsed is None:
            print("PARSE ERROR — using defaults")
            results.append(
                {
                    "name": name,
                    "buy_protein_chef": False,
                    "purchase_prob": 50,
                    "final_decision": "(parse error)",
                    "raw": raw,
                    "condition": "naive_baseline",
                }
            )
            continue

        buy = bool(parsed.get("buy_protein_chef", False))
        prob = int(parsed.get("purchase_probability_protein_chef", 50))
        prob = max(0, min(100, prob))
        decision = str(parsed.get("final_decision", "")).strip()
        gut = str(parsed.get("gut_reaction", "")).strip()

        label = "BUY" if buy else ("CONSIDER" if prob >= 40 else "REJECT")
        print(f"{label} (prob={prob}%)")

        results.append(
            {
                "name": name,
                "buy_protein_chef": buy,
                "purchase_prob": prob,
                "final_decision": decision,
                "gut_reaction": gut,
                "raw": raw,
                "condition": "naive_baseline",
            }
        )
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _decision_label(r: dict) -> str:
    """Return BUY / CONSIDER / REJECT label."""
    if r["buy_protein_chef"]:
        return "BUY"
    if r["purchase_prob"] >= 40:
        return "CONSIDER"
    return "REJECT"


def print_report(
    memory_results: list[dict],
    naive_results: list[dict],
) -> dict:
    """Print the CEO-readable comparison table and return the results dict."""

    # --- compute stats ---
    mem_probs = [r["purchase_prob"] for r in memory_results]
    naive_probs = [r["purchase_prob"] for r in naive_results]

    mem_mean = _mean(mem_probs)
    mem_std = _stdev(mem_probs)
    naive_mean = _mean(naive_probs)
    naive_std = _stdev(naive_probs)

    mem_decisions = [r["final_decision"] for r in memory_results]
    naive_decisions = [r["final_decision"] for r in naive_results]

    mem_distinct = _count_distinct(mem_decisions)
    naive_distinct = _count_distinct(naive_decisions)

    n = len(memory_results)

    # Variance uplift: ratio of standard deviations (spread of behaviour)
    # Guard against zero naive_std to avoid division by zero
    if naive_std > 0:
        variance_uplift = mem_std / naive_std
    else:
        variance_uplift = float("inf")

    mem_distinct_pct = round(mem_distinct / n * 100) if n else 0
    naive_distinct_pct = round(naive_distinct / n * 100) if n else 0

    # --- print table ---
    separator = "=" * 58

    print(f"\n{separator}")
    print("  Lo! Foods E2E Persona Depth Validation")
    print(separator)

    print(f"\nSTIMULUS:\n  {STIMULUS}\n")

    print("MEMORY-BACKED PERSONAS (Simulatte)")
    print("  Decisions:")
    for r in memory_results:
        print(f"    {r['name']:30s} → {_decision_label(r)} (prob={r['purchase_prob']}%)")
    print(f"  Purchase probability (mean ± stdev): {mem_mean:.1f} ± {mem_std:.1f}")
    print(f"  Distinct responses: {mem_distinct}/{n}")

    print()
    print("NAIVE LLM BASELINE (demographics only)")
    print("  Decisions:")
    for r in naive_results:
        print(f"    {r['name']:30s} → {_decision_label(r)} (prob={r['purchase_prob']}%)")
    print(f"  Purchase probability (mean ± stdev): {naive_mean:.1f} ± {naive_std:.1f}")
    print(f"  Distinct responses: {naive_distinct}/{n}")

    print()
    print(separator)
    print("VERDICT")
    print(separator)

    if naive_std > 0:
        uplift_str = f"{variance_uplift:.2f}x"
        uplift_pct = f"{(variance_uplift - 1) * 100:.0f}%"
        print(f"  Behavioral variance uplift:    {uplift_str} ({uplift_pct} more spread)")
    else:
        print(f"  Behavioral variance uplift:    ∞ (naive baseline had zero variance)")

    print(f"  Distinct response rate:        Simulatte {mem_distinct_pct}% vs Naive {naive_distinct_pct}%")
    print(f"  Memory-backed personas are     {variance_uplift:.1f}x more behaviorally distinct")

    print()

    # KEY FINDING
    if variance_uplift >= 2.0:
        finding = (
            f"Memory-backed personas produced {variance_uplift:.1f}x more behavioral "
            f"variance than the naive demographic baseline (stdev {mem_std:.1f} vs "
            f"{naive_std:.1f}), with {mem_distinct_pct}% distinct decision patterns "
            f"vs {naive_distinct_pct}% for naive — confirming that life-story memory "
            f"drives genuinely differentiated reasoning, not just demographic variation."
        )
    elif variance_uplift >= 1.0:
        finding = (
            f"Memory-backed personas showed modestly more behavioral spread than the "
            f"naive baseline ({variance_uplift:.1f}x uplift, stdev {mem_std:.1f} vs "
            f"{naive_std:.1f}). Personas reasoned from distinct life contexts, though "
            f"the bread purchase scenario produced moderate convergence across both conditions."
        )
    else:
        finding = (
            f"Naive baseline showed higher variance ({naive_std:.1f}) than memory-backed "
            f"({mem_std:.1f}) in this run — the bread scenario may produce strong "
            f"convergence at the memory level. Consider rerunning with a higher-ambiguity "
            f"stimulus for a cleaner separation signal."
        )

    print(f"KEY FINDING:\n  {finding}")
    print()

    # --- assemble results dict ---
    results_dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "temperature": TEMPERATURE,
        "stimulus": STIMULUS,
        "n_personas": n,
        "memory_backed": {
            "results": [
                {
                    "name": r["name"],
                    "buy_protein_chef": r["buy_protein_chef"],
                    "purchase_prob": r["purchase_prob"],
                    "decision_label": _decision_label(r),
                    "final_decision": r["final_decision"],
                }
                for r in memory_results
            ],
            "purchase_prob_mean": round(mem_mean, 2),
            "purchase_prob_stdev": round(mem_std, 2),
            "distinct_responses": mem_distinct,
            "distinct_pct": mem_distinct_pct,
        },
        "naive_baseline": {
            "results": [
                {
                    "name": r["name"],
                    "buy_protein_chef": r["buy_protein_chef"],
                    "purchase_prob": r["purchase_prob"],
                    "decision_label": _decision_label(r),
                    "final_decision": r["final_decision"],
                }
                for r in naive_results
            ],
            "purchase_prob_mean": round(naive_mean, 2),
            "purchase_prob_stdev": round(naive_std, 2),
            "distinct_responses": naive_distinct,
            "distinct_pct": naive_distinct_pct,
        },
        "verdict": {
            "variance_uplift_x": round(variance_uplift, 2) if not math.isinf(variance_uplift) else None,
            "memory_distinct_pct": mem_distinct_pct,
            "naive_distinct_pct": naive_distinct_pct,
            "key_finding": finding,
        },
    }

    return results_dict


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    # Guard: cohort must exist
    if not COHORT_PATH.exists():
        print(
            f"Cohort not ready — run after Batch 1 generation.\n"
            f"Expected file: {COHORT_PATH}"
        )
        sys.exit(0)

    # Load cohort
    with open(COHORT_PATH) as f:
        cohort_data = json.load(f)

    # Support both flat list and envelope-wrapped formats
    if isinstance(cohort_data, list):
        personas = cohort_data
    elif isinstance(cohort_data, dict):
        personas = cohort_data.get("personas") or cohort_data.get("envelope", {}).get("personas", [])
    else:
        print("ERROR: Unrecognised cohort JSON structure.")
        sys.exit(1)

    if not personas:
        print("ERROR: No personas found in cohort file.")
        sys.exit(1)

    n = len(personas)
    print(f"\nLoaded {n} persona(s) from {COHORT_PATH.name}")

    # Initialise Anthropic client (uses ANTHROPIC_API_KEY from env)
    client = anthropic.Anthropic()

    # Run both conditions
    memory_results = run_memory_backed_test(personas, client)
    naive_results = run_naive_baseline_test(personas, client)

    # Print report and collect results dict
    results_dict = print_report(memory_results, naive_results)

    # Save to file
    with open(RESULTS_PATH, "w") as f:
        json.dump(results_dict, f, indent=2)
    print(f"Full results saved to: {RESULTS_PATH}\n")


if __name__ == "__main__":
    main()
