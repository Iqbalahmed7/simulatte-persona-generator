"""
UAT: end-to-end persona generation test
Tests the exact code path used by /generate-persona on Railway.

Run:  PYTHONPATH=. python3 uat_generation.py
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Load env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("❌  ANTHROPIC_API_KEY not set"); sys.exit(1)

# Add pilots/the-mind/api to path so we can import main.py directly
# (the directory name uses hyphens, so normal package imports won't work)
sys.path.insert(0, str(Path(__file__).parent / "pilots" / "the-mind" / "api"))

import anthropic

# ── import the functions under test ─────────────────────────────────────────
from main import (
    _extract_from_brief,
    _generate_persona_direct,
    _persist_generated_dict,
    _GENERATED_DIR,
)


BRIEF = (
    "Ravi, 34, software engineer in Bangalore. "
    "Single, rents an apartment, earns ₹18L/year. "
    "Buys gadgets impulsively, healthy eating aspirations, "
    "active on Reddit and YouTube, uses 5 streaming subscriptions."
)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "


def check(label: str, value, nonempty=True):
    ok = bool(value) if nonempty else value is not None
    icon = PASS if ok else FAIL
    display = str(value)[:80] if isinstance(value, str) else repr(value)[:80]
    print(f"  {icon}  {label}: {display}")
    return ok


async def run():
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    failures = 0

    # ── Step 1: extract brief ────────────────────────────────────────────────
    print("\n─── Step 1: _extract_from_brief ───────────────────────────────")
    t0 = time.monotonic()
    anchor, domain, biz = await _extract_from_brief(BRIEF, None, client)
    elapsed = time.monotonic() - t0
    print(f"  ⏱  {elapsed:.1f}s")
    failures += 0 if check("anchor keys", list(anchor.keys())) else 1
    failures += 0 if check("domain", domain) else 1
    failures += 0 if check("biz problem", biz) else 1
    print(f"  anchor = {json.dumps(anchor, indent=2)}")

    # ── Step 2: generate persona (both parallel Haiku calls) ─────────────────
    print("\n─── Step 2: _generate_persona_direct ─────────────────────────")
    t0 = time.monotonic()
    persona_dict = await _generate_persona_direct(
        brief=BRIEF,
        anchor=anchor,
        domain=domain,
        client=client,
    )
    elapsed = time.monotonic() - t0
    print(f"  ⏱  {elapsed:.1f}s")

    # ── Step 3: validate all fields the persona page accesses ────────────────
    print("\n─── Step 3: Field validation (persona page requirements) ──────")

    da = persona_dict.get("demographic_anchor", {})
    di = persona_dict.get("derived_insights", {})
    bt = persona_dict.get("behavioural_tendencies", {})
    mem = (persona_dict.get("memory") or {}).get("core", {})
    narr = persona_dict.get("narrative", {})

    failures += 0 if check("persona_id", persona_dict.get("persona_id")) else 1
    failures += 0 if check("name", da.get("name")) else 1
    failures += 0 if check("age", da.get("age"), nonempty=False) else 1
    failures += 0 if check("location.city", (da.get("location") or {}).get("city")) else 1
    failures += 0 if check("location.country", (da.get("location") or {}).get("country")) else 1
    failures += 0 if check("life_stage", da.get("life_stage")) else 1
    failures += 0 if check("education", da.get("education")) else 1
    failures += 0 if check("employment.occupation", (da.get("employment") or {}).get("occupation")) else 1
    failures += 0 if check("employment.industry", (da.get("employment") or {}).get("industry")) else 1
    failures += 0 if check("employment.seniority", (da.get("employment") or {}).get("seniority")) else 1
    failures += 0 if check("household.size", (da.get("household") or {}).get("size"), nonempty=False) else 1
    failures += 0 if check("household.composition", (da.get("household") or {}).get("composition")) else 1

    failures += 0 if check("narrative.third_person", narr.get("third_person")) else 1
    failures += 0 if check("narrative.first_person", narr.get("first_person")) else 1

    failures += 0 if check("derived_insights.decision_style", di.get("decision_style")) else 1
    failures += 0 if check("derived_insights.trust_anchor", di.get("trust_anchor")) else 1
    failures += 0 if check("derived_insights.risk_appetite", di.get("risk_appetite")) else 1
    failures += 0 if check("derived_insights.primary_value_orientation", di.get("primary_value_orientation")) else 1
    failures += 0 if check("derived_insights.consistency_score", di.get("consistency_score"), nonempty=False) else 1
    failures += 0 if check("derived_insights.key_tensions (list)", di.get("key_tensions"), nonempty=False) else 1

    failures += 0 if check("bt.trust_orientation (dict)", bt.get("trust_orientation"), nonempty=False) else 1
    failures += 0 if check("bt.price_sensitivity.band", (bt.get("price_sensitivity") or {}).get("band")) else 1
    failures += 0 if check("bt.price_sensitivity.description", (bt.get("price_sensitivity") or {}).get("description")) else 1
    failures += 0 if check("bt.objection_profile (list)", bt.get("objection_profile"), nonempty=False) else 1

    failures += 0 if check("memory.core.identity_statement", mem.get("identity_statement")) else 1
    failures += 0 if check("memory.core.key_values (list)", mem.get("key_values"), nonempty=False) else 1
    failures += 0 if check("memory.core.life_defining_events (list)", mem.get("life_defining_events"), nonempty=False) else 1

    failures += 0 if check("decision_bullets (list)", persona_dict.get("decision_bullets"), nonempty=False) else 1
    failures += 0 if check("life_stories (list)", persona_dict.get("life_stories"), nonempty=False) else 1

    # Check life_stories have title + narrative
    stories = persona_dict.get("life_stories") or []
    for i, s in enumerate(stories[:3]):
        failures += 0 if check(f"life_stories[{i}].title", s.get("title")) else 1
        failures += 0 if check(f"life_stories[{i}].narrative", s.get("narrative")) else 1

    # ── Step 4: persist to disk ──────────────────────────────────────────────
    print("\n─── Step 4: _persist_generated_dict ──────────────────────────")
    try:
        _persist_generated_dict(persona_dict)
        pid = persona_dict["persona_id"]
        disk_path = _GENERATED_DIR / f"{pid}.json"
        if disk_path.exists():
            on_disk = json.loads(disk_path.read_text())
            print(f"  {PASS}  Written to disk: {disk_path}")
            failures += 0 if check("disk.persona_id matches", on_disk.get("persona_id") == pid, nonempty=False) else 1
        else:
            print(f"  {FAIL}  File not found after persist: {disk_path}")
            failures += 1
    except Exception as e:
        print(f"  {FAIL}  _persist_generated_dict raised: {e}")
        failures += 1

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n─── Result ────────────────────────────────────────────────────")
    if failures == 0:
        print(f"  {PASS}  ALL CHECKS PASSED — persona_id: {persona_dict['persona_id']}")
        print(f"  {PASS}  Name: {da.get('name')}, {da.get('age')}, {(da.get('location') or {}).get('city')}")
        print(f"\n  The /generate-persona → /persona/[id] flow will work end-to-end.")
    else:
        print(f"  {FAIL}  {failures} check(s) FAILED — see above for details.")

    return failures


if __name__ == "__main__":
    result = asyncio.run(run())
    sys.exit(0 if result == 0 else 1)
