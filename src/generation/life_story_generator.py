"""Life Story Generator — Sprint 2, Codex.

Generates 2–3 psychologically grounded life story vignettes for a persona,
each derived from and traceable to the filled attribute profile.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.schema.persona import Attribute, DemographicAnchor, LifeStory
from src.taxonomy.base_taxonomy import BASE_TAXONOMY, TAXONOMY_BY_NAME
from src.utils.retry import api_call_with_retry


# ── Anchor attribute names (always included in the prompt) ─────────────────────
_ANCHOR_NAMES: list[str] = [
    attr.name for attr in BASE_TAXONOMY if attr.is_anchor
]

# ── Label helpers ───────────────────────────────────────────────────────────────

def _label_continuous(value: float) -> str:
    """Returns a human-readable band label for a continuous 0–1 attribute."""
    if value <= 0.2:
        return "very low"
    if value <= 0.4:
        return "low"
    if value <= 0.6:
        return "moderate"
    if value <= 0.8:
        return "high"
    return "very high"


def _format_attribute_line(name: str, attr: Attribute) -> str:
    """Returns a single prompt line for one attribute."""
    if attr.type == "continuous":
        band = _label_continuous(float(attr.value))
        return f"- {name}: {attr.value:.2f} ({band})"
    return f"- {name}: {attr.value}"


# ── Attribute selection ─────────────────────────────────────────────────────────

def _select_top_attributes(
    attributes: dict[str, dict[str, Attribute]],
) -> list[tuple[str, Attribute]]:
    """
    Returns the 10 highest-signal attributes for the life story prompt.

    Priority:
      1. All 8 anchor attributes (always included, in anchor_order).
      2. The 2 non-anchor continuous attributes with values furthest from 0.5
         (highest |value - 0.5|), giving the most extreme psychological signal.
    """
    # Flatten attributes dict into name → Attribute
    flat: dict[str, Attribute] = {}
    for category_attrs in attributes.values():
        flat.update(category_attrs)

    # 1. Anchors
    anchor_attrs: list[tuple[str, Attribute]] = []
    anchor_defs_sorted = sorted(
        [a for a in BASE_TAXONOMY if a.is_anchor],
        key=lambda a: (a.anchor_order or 99),
    )
    for defn in anchor_defs_sorted:
        if defn.name in flat:
            anchor_attrs.append((defn.name, flat[defn.name]))

    anchor_name_set = {n for n, _ in anchor_attrs}

    # 2. Non-anchor continuous extremes
    non_anchor_continuous: list[tuple[str, Attribute, float]] = []
    for name, attr in flat.items():
        if name not in anchor_name_set and attr.type == "continuous":
            distance = abs(float(attr.value) - 0.5)
            non_anchor_continuous.append((name, attr, distance))

    non_anchor_continuous.sort(key=lambda x: x[2], reverse=True)
    extreme_two = [(n, a) for n, a, _ in non_anchor_continuous[:2]]

    return anchor_attrs + extreme_two


# ── Prompt builders ─────────────────────────────────────────────────────────────

def _build_user_prompt(
    demographic_anchor: DemographicAnchor,
    attributes: dict[str, dict[str, Attribute]],
    n_stories: int,
) -> str:
    da = demographic_anchor
    loc = da.location
    hh = da.household

    demo_block = (
        f"- Age: {da.age}, Gender: {da.gender}, "
        f"Location: {loc.city}, {loc.urban_tier}\n"
        f"- Life stage: {da.life_stage}, Education: {da.education}, "
        f"Employment: {da.employment}\n"
        f"- Household: {hh.structure}, size {hh.size}, "
        f"income: {hh.income_bracket}"
    )

    selected = _select_top_attributes(attributes)
    attr_lines = "\n".join(_format_attribute_line(n, a) for n, a in selected)

    return (
        f"Demographics:\n{demo_block}\n\n"
        f"Key attribute profile (decision-relevant):\n{attr_lines}\n\n"
        f"Generate exactly {n_stories} life story vignettes. Each story must:\n"
        "1. Have a specific, named event (not \"went through a difficult time\" — "
        "something precise)\n"
        "2. Occur at a realistic age for this person\n"
        "3. Have a lasting impact that explains one of their current attribute values\n"
        "4. Be 2–3 sentences maximum\n\n"
        "Return JSON only:\n"
        "[\n"
        "  {\"title\": \"...\", \"when\": \"age 24\", \"event\": \"...\", "
        "\"lasting_impact\": \"...\"},\n"
        "  ...\n"
        "]"
    )


_SYSTEM_PROMPT = (
    "You are constructing life story vignettes for a synthetic persona.\n"
    "Each story must emerge naturally from this specific person's psychology and values.\n"
    "Do not invent generic life events — derive each story from the attribute profile provided."
)

# ── when-field validation ───────────────────────────────────────────────────────

_WHEN_PATTERN = re.compile(
    r"^(age\s+\d+|at\s+\d+|\d+\s+years?\s+old|\d{4})$",
    re.IGNORECASE,
)


def _valid_when(when: str) -> bool:
    return bool(_WHEN_PATTERN.match(when.strip()))


# ── Fallback story ──────────────────────────────────────────────────────────────

def _fallback_story(index: int, demographic_anchor: DemographicAnchor) -> LifeStory:
    """Returns a minimal coherent fallback vignette when the LLM under-delivers."""
    age_ref = max(18, demographic_anchor.age - 10 - index * 3)
    return LifeStory(
        title=f"Formative experience {index + 1}",
        when=f"age {age_ref}",
        event=(
            f"At {age_ref}, {demographic_anchor.name} faced a significant "
            "personal crossroads that required a difficult trade-off between "
            "immediate desires and long-term stability."
        ),
        lasting_impact=(
            "This event reinforced a cautious approach to major decisions "
            "and a preference for known, reliable options."
        ),
    )


# ── Parsing ─────────────────────────────────────────────────────────────────────

def _parse_stories(raw: str) -> list[dict] | None:
    """
    Extracts the JSON array from the LLM response.
    Returns None if parsing fails entirely.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Try direct parse first
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Attempt to extract array substring
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(cleaned[start : end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _coerce_story(raw_item: dict) -> LifeStory | None:
    """Tries to build a LifeStory from a dict; returns None on failure."""
    title = str(raw_item.get("title", "")).strip()
    when = str(raw_item.get("when", "")).strip()
    event = str(raw_item.get("event", "")).strip()
    lasting_impact = str(raw_item.get("lasting_impact", "")).strip()

    if not (title and event and lasting_impact):
        return None

    # Normalise missing or invalid when
    if not when or not _valid_when(when):
        when = when or "age unknown"

    return LifeStory(title=title, when=when, event=event, lasting_impact=lasting_impact)


# ── Main class ──────────────────────────────────────────────────────────────────

class LifeStoryGenerator:
    """Generates 2–3 life story vignettes grounded in the persona's attribute profile."""

    def __init__(self, llm_client: Any, model: str = "claude-sonnet-4-6") -> None:
        self.llm = llm_client
        self.model = model

    async def generate(
        self,
        demographic_anchor: DemographicAnchor,
        attributes: dict[str, dict[str, Attribute]],
        n_stories: int = 3,
        llm_client: Any = None,
    ) -> list[LifeStory]:
        """
        Generates n_stories (2 or 3) life story vignettes.
        Each story is grounded in the persona's attribute profile.
        Returns a list of LifeStory objects (always 2–3 items).

        Args:
            llm_client: Optional BaseLLMClient. If provided, routing goes through
                        llm_client.complete(). Otherwise falls back to self.llm.messages.create().
        """
        n_stories = max(2, min(3, n_stories))

        user_prompt = _build_user_prompt(demographic_anchor, attributes, n_stories)

        stories = await self._call_and_parse(
            demographic_anchor, user_prompt, n_stories, attempt=1, llm_client=llm_client
        )

        # Retry once if we got too few
        if len(stories) < 2:
            stories = await self._call_and_parse(
                demographic_anchor, user_prompt, n_stories, attempt=2, llm_client=llm_client
            )

        # Pad with fallbacks if still insufficient
        while len(stories) < 2:
            stories.append(_fallback_story(len(stories), demographic_anchor))

        # Trim to at most 3
        return stories[:3]

    async def _call_and_parse(
        self,
        demographic_anchor: DemographicAnchor,
        user_prompt: str,
        n_stories: int,
        attempt: int,
        llm_client: Any = None,
    ) -> list[LifeStory]:
        """Calls the LLM, parses the response, and returns whatever valid stories it produced."""
        extra_note = (
            f"\n\nIMPORTANT: You must return exactly {n_stories} stories. "
            "Previous attempt returned too few."
            if attempt > 1
            else ""
        )

        full_user_prompt = user_prompt + extra_note

        if llm_client is not None and hasattr(llm_client, 'complete'):
            raw_text = await llm_client.complete(
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": full_user_prompt}],
                max_tokens=1024,
                model=self.model,
            )
        else:
            response = await api_call_with_retry(
                self.llm.messages.create,
                model=self.model,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": full_user_prompt}],
            )
            raw_text = response.content[0].text
        parsed = _parse_stories(raw_text)

        if parsed is None:
            return []

        stories: list[LifeStory] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            story = _coerce_story(item)
            if story is not None:
                stories.append(story)

        return stories
