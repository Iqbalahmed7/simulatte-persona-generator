"""LLM-driven DemographicAnchor sampler (PR-PG-3).

Generates fresh, brief-tailored DemographicAnchors via Anthropic for
non-Pew "general" runs.  The legacy fixed-pool sampler in
``demographic_sampler.sample_demographic_anchor`` remains the default
for ``study_type='pew_calibration'`` runs whose calibration validity
depends on the existing name + political-lean tagging.

Public entry point::

    anchor = await sample_anchor_llm(
        business_problem=...,
        icp_description=...,
        market="India",
        age_min=22,
        age_max=55,
        persona_index=3,
        domain="india_general",
    )

On any LLM / parse / validation failure the caller is expected to fall
back to the legacy fixed-pool sampler (see identity_constructor wiring).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.schema.persona import DemographicAnchor, Household, Location
from src.utils.retry import api_call_with_retry

logger = logging.getLogger(__name__)


# Same model family used by attribute_filler / narrative_generator for
# generation work — Sonnet for anchor coherence.  Override via env if
# the rest of the project switches.
_ANCHOR_MODEL = "claude-sonnet-4-6"
_TEMPERATURE = 0.9  # high-ish, we want diversity within a cohort
_MAX_TOKENS = 600


_SCHEMA_SPEC = """{
  "name": "<full name; culturally appropriate for the market>",
  "age": <integer in age_min..age_max>,
  "gender": "<one of: female | male | non-binary>",
  "location": {
    "country": "<country>",
    "region": "<state / region>",
    "city": "<city>",
    "urban_tier": "<one of: metro | tier2 | tier3 | rural>"
  },
  "household": {
    "structure": "<one of: nuclear | joint | single-parent | couple-no-kids | other>",
    "size": <integer 1..10>,
    "income_bracket": "<lower | middle | upper, with optional qualifier e.g. 'lower-middle'>",
    "dual_income": <true | false>
  },
  "life_stage": "<short phrase e.g. 'parent of school-age children', 'early-career professional'>",
  "education": "<one of: high-school | undergraduate | postgraduate | doctoral>",
  "employment": "<one of: full-time | part-time | self-employed | homemaker | student | retired>"
}"""


def _build_prompt(
    business_problem: str,
    icp_description: str,
    market: str,
    age_min: int,
    age_max: int,
    persona_index: int,
) -> str:
    return f"""You are generating ONE realistic demographic anchor for a synthetic persona.

## Research context
Study: {business_problem}
Target audience: {icp_description}
Market: {market}
Age range: {age_min}-{age_max}
This is persona #{persona_index} in a cohort — pick someone who feels DIFFERENT from typical members of this audience. Add diversity in occupation, region, household structure, and life stage.

## Schema (return JSON only, exact keys, no markdown fence)
{_SCHEMA_SPEC}

Be specific.  Use real names appropriate to the market (e.g. real Indian names if market is India, real US names if US).  The occupation, life_stage, and household must be plausible for the target audience.  Don't invent fictional companies.  Don't include political party preferences unless directly relevant to the brief.

Return ONLY the JSON object — no prose, no markdown fence."""


def _strip_fence(raw: str) -> str:
    raw = raw.strip()
    if "```" in raw:
        # Take the first fenced block content
        parts = raw.split("```")
        # parts[1] may start with 'json\n...'
        body = parts[1] if len(parts) >= 2 else raw
        if body.lstrip().lower().startswith("json"):
            body = body.lstrip()[4:]
        return body.strip()
    return raw


def _coerce_anchor(parsed: dict[str, Any]) -> DemographicAnchor:
    """Validate the LLM's JSON against the DemographicAnchor schema.

    Pydantic will raise ValidationError if any Literal field is off-list
    (gender / urban_tier / household.structure / education / employment).
    """
    location = Location(**parsed["location"])
    household = Household(**parsed["household"])
    return DemographicAnchor(
        name=parsed["name"],
        age=int(parsed["age"]),
        gender=parsed["gender"],
        location=location,
        household=household,
        life_stage=parsed["life_stage"],
        education=parsed["education"],
        employment=parsed["employment"],
        worldview=None,  # LLM path leaves worldview unset; downstream handles None
    )


async def sample_anchor_llm(
    llm_client: Any,
    business_problem: str,
    icp_description: str,
    market: str,
    age_min: int,
    age_max: int,
    persona_index: int,
    domain: str = "india_general",
    model: str = _ANCHOR_MODEL,
) -> DemographicAnchor:
    """Generate a fresh, brief-tailored DemographicAnchor via the LLM.

    Args:
        llm_client: AsyncAnthropic-compatible client (anthropic.AsyncAnthropic()).
        business_problem: The research question driving the cohort.
        icp_description: Free-text ICP / target audience description.
        market: Country/region label (e.g. "India", "USA") used in the prompt
            for name/locale realism.
        age_min: Lower bound (inclusive) for sampled age.
        age_max: Upper bound (inclusive) for sampled age.
        persona_index: 0-based index in the cohort, threaded into the prompt
            so the LLM can intentionally diversify across the run.
        domain: Domain key passed through unchanged (purely for logging).
        model: Anthropic model id; defaults to Sonnet for coherence.

    Returns:
        A fully-populated, schema-valid ``DemographicAnchor``.

    Raises:
        Any exception from the LLM call, JSON parse, or Pydantic validation.
        Callers are expected to fall back to the legacy fixed-pool sampler
        on failure (see identity_constructor wiring).
    """
    prompt = _build_prompt(
        business_problem=business_problem,
        icp_description=icp_description,
        market=market,
        age_min=age_min,
        age_max=age_max,
        persona_index=persona_index,
    )

    response = await api_call_with_retry(
        llm_client.messages.create,
        model=model,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    cleaned = _strip_fence(raw_text)
    parsed = json.loads(cleaned)

    # Defensive age clamp — LLM occasionally drifts a year or two outside.
    try:
        a = int(parsed.get("age", age_min))
        if a < age_min or a > age_max:
            parsed["age"] = max(age_min, min(age_max, a))
    except (TypeError, ValueError):
        parsed["age"] = (age_min + age_max) // 2

    anchor = _coerce_anchor(parsed)
    logger.info(
        "anchor_sampler: LLM-sampled anchor name=%r age=%d market=%s domain=%s index=%d",
        anchor.name, anchor.age, market, domain, persona_index,
    )
    return anchor


__all__ = ["sample_anchor_llm"]
