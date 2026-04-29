"""identity_constructor.py — Sprint 2, Cursor

Orchestration layer that runs the full 8-step identity build sequence for a
single persona and returns a validated PersonaRecord.

Build sequence (strict order per brief):
  Step 1  AttributeFiller.fill()
  Step 2  DerivedInsightsComputer.compute()
  Step 3  LifeStoryGenerator.generate()
  Step 4  TendencyEstimator.estimate()
  Step 5  NarrativeGenerator.generate()
  Step 6  _assemble_core_memory()
  Step 7  PersonaValidator.validate_all()
  Step 8  Return PersonaRecord

Sprint 2 parallel build note
----------------------------
DerivedInsightsComputer, LifeStoryGenerator, TendencyEstimator, and
NarrativeGenerator are written in parallel by Goose and Codex.  Their files
may not exist when this module is first imported.  Each is guarded by a
try/except ImportError block so the module remains importable at any point
during the parallel build.  At runtime (when .build() is called) all four
must be present; if they are not, a clear ImportError is raised naming the
missing module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.observability.cost_tracer import CostTracer
from src.schema.persona import (
    CoreMemory,
    DemographicAnchor,
    ImmutableConstraints,
    LifeDefiningEvent,
    Memory,
    PersonaRecord,
    RelationshipMap,
    SimulationState,
    WorkingMemory,
)
from src.taxonomy.domain_templates.template_loader import (
    get_domain_attributes,
    load_taxonomy,
)
from src.generation.attribute_filler import AttributeFiller
from src.schema.validators import PersonaValidator
from src.memory.core_memory import assemble_core_memory

# ---------------------------------------------------------------------------
# Sprint-2 parallel-build guards
# ---------------------------------------------------------------------------
# Each component is imported inside a try/except so this module can be
# imported (and its dataclasses used) even before the parallel Sprint 2
# files land.  Runtime calls to .build() will fail fast with a clear message
# if any component is absent.

try:
    from src.generation.derived_insights import DerivedInsightsComputer
    _DERIVED_INSIGHTS_AVAILABLE = True
except ImportError:
    _DERIVED_INSIGHTS_AVAILABLE = False
    if not TYPE_CHECKING:
        DerivedInsightsComputer = None  # type: ignore[assignment,misc]

try:
    from src.generation.life_story_generator import LifeStoryGenerator
    _LIFE_STORY_AVAILABLE = True
except ImportError:
    _LIFE_STORY_AVAILABLE = False
    if not TYPE_CHECKING:
        LifeStoryGenerator = None  # type: ignore[assignment,misc]

try:
    from src.generation.tendency_estimator import TendencyEstimator
    _TENDENCY_AVAILABLE = True
except ImportError:
    _TENDENCY_AVAILABLE = False
    if not TYPE_CHECKING:
        TendencyEstimator = None  # type: ignore[assignment,misc]

try:
    from src.generation.narrative_generator import NarrativeGenerator
    _NARRATIVE_AVAILABLE = True
except ImportError:
    _NARRATIVE_AVAILABLE = False
    if not TYPE_CHECKING:
        NarrativeGenerator = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GENERATOR_VERSION = "2.1.0"

# Number of life stories to request (2 or 3 — spec allows 2–3).
_DEFAULT_N_STORIES = 3

# Word budget for identity_statement (first 25 words of first_person).
_IDENTITY_STATEMENT_WORDS = 25


# ---------------------------------------------------------------------------
# ICPSpec
# ---------------------------------------------------------------------------

@dataclass
class ICPSpec:
    """User-provided specification for persona generation.

    Exported from this module so that other files (e.g. narrative_generator)
    can import it via: from src.generation.identity_constructor import ICPSpec
    """

    domain: str
    """e.g. 'cpg', 'saas'"""

    mode: str
    """'quick' | 'deep' | 'simulation-ready' | 'grounded'"""

    anchor_overrides: dict[str, Any] = field(default_factory=dict)
    """Forced attribute values; applied after anchor filling."""

    persona_id_prefix: str = "default"
    """Used in persona_id: pg-[prefix]-[NNN]."""

    persona_index: int = 1
    """The NNN in persona_id, zero-padded to 3 digits."""

    domain_data: list[str] | None = None
    """Raw text strings (reviews, posts) for grounding. When provided and
    mode='grounded', assemble_cohort() will run the grounding pipeline to
    upgrade tendency sources from 'proxy' to 'grounded'."""

    sarvam_enabled: bool = False
    """When True and persona country is 'India', route LLM calls to SarvamLLMClient."""


# ---------------------------------------------------------------------------
# IdentityConstructor
# ---------------------------------------------------------------------------

class IdentityConstructor:
    """Orchestrates the full 8-step identity build sequence.

    All LLM calls are delegated to component classes — none are made inline.
    """

    def __init__(self, llm_client: Any, model: str = "claude-sonnet-4-6") -> None:
        self.llm = llm_client
        self.model = model

        # Attribute filling is mechanical (discrete categoricals) so we use a
        # cheaper model by default — ~12× less expensive on output tokens.
        # Override via PG_FILLER_MODEL env var; set to GENERATION_MODEL value
        # to use a single model for everything.
        import os as _os
        filler_model = _os.getenv("PG_FILLER_MODEL", "claude-haiku-4-5-20251001")

        # Step 1 component — always available (Sprint 1).
        self.filler = AttributeFiller(llm_client, filler_model)

        # Validator — always available (Sprint 1).
        self.validator = PersonaValidator()

        # Steps 2 & 4 — deterministic, no LLM (Goose Sprint 2).
        self.insights_computer = (
            DerivedInsightsComputer() if _DERIVED_INSIGHTS_AVAILABLE else None
        )
        self.tendency_estimator = (
            TendencyEstimator() if _TENDENCY_AVAILABLE else None
        )

        # Steps 3 & 5 — LLM-calling (Codex Sprint 2).
        self.story_generator = (
            LifeStoryGenerator(llm_client, model) if _LIFE_STORY_AVAILABLE else None
        )
        self.narrative_generator = (
            NarrativeGenerator(llm_client, model) if _NARRATIVE_AVAILABLE else None
        )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def build(
        self,
        demographic_anchor: DemographicAnchor,
        icp_spec: ICPSpec,
    ) -> PersonaRecord:
        """Run the full identity build sequence.

        Returns a validated PersonaRecord.
        Raises ImportError if any Sprint 2 component is not yet installed.
        Raises ValueError if PersonaValidator detects a gate failure (G1/G2/G3).

        If icp_spec.mode == "grounded", the returned persona will have mode="grounded"
        but tendency sources will still be "proxy" until assemble_cohort() is called
        with domain_data — which upgrades tendencies via the grounding pipeline.
        """
        self._assert_components_available()
        persona_id = self._make_persona_id(icp_spec)
        CostTracer.start_persona(persona_id)

        # ---------------------------------------------------------------
        # Step 1 — Fill all attributes
        # ---------------------------------------------------------------
        CostTracer.set_phase("attribute_fill")
        taxonomy = load_taxonomy(icp_spec.domain)
        domain_attrs = get_domain_attributes(icp_spec.domain)

        attributes = await self.filler.fill(
            demographic_anchor=demographic_anchor,
            taxonomy=taxonomy,
            anchor_overrides=icp_spec.anchor_overrides,
            domain_attrs=domain_attrs,
        )

        # ---------------------------------------------------------------
        # Routing — determine LLM client after anchor is available
        # Route to Sarvam for India personas when sarvam_enabled=True.
        # ---------------------------------------------------------------
        from src.utils.llm_router import get_llm_client
        from src.sarvam.llm_client import BaseLLMClient
        _country = demographic_anchor.location.country
        _llm_client: BaseLLMClient = get_llm_client(
            self.llm,
            sarvam_enabled=icp_spec.sarvam_enabled,
            country=_country,
        )

        # ---------------------------------------------------------------
        # Step 2 — Compute derived insights
        # ---------------------------------------------------------------
        CostTracer.set_phase("identity_core")
        derived_insights = self.insights_computer.compute(
            attributes=attributes,
            demographic_anchor=demographic_anchor,
        )

        # ---------------------------------------------------------------
        # Step 3 — Generate life stories
        # ---------------------------------------------------------------
        CostTracer.set_phase("life_story")
        life_stories = await self.story_generator.generate(
            demographic_anchor=demographic_anchor,
            attributes=attributes,
            n_stories=_DEFAULT_N_STORIES,
            llm_client=_llm_client,
        )

        # ---------------------------------------------------------------
        # Step 4 — Estimate tendencies
        # (must follow Step 2 — tendencies reference derived_insights)
        # ---------------------------------------------------------------
        CostTracer.set_phase("identity_behavior")
        behavioural_tendencies = self.tendency_estimator.estimate(
            attributes=attributes,
            derived_insights=derived_insights,
        )

        # ---------------------------------------------------------------
        # Step 5 — Generate narrative
        # (must follow Step 3 — narrative references life story events)
        # ---------------------------------------------------------------
        CostTracer.set_phase("identity_behavior")
        narrative = await self.narrative_generator.generate(
            demographic_anchor=demographic_anchor,
            attributes=attributes,
            derived_insights=derived_insights,
            life_stories=life_stories,
            behavioural_tendencies=behavioural_tendencies,
            llm_client=_llm_client,
        )

        # ---------------------------------------------------------------
        # Step 6 — Assemble core memory
        # ---------------------------------------------------------------
        partial_record: dict[str, Any] = {
            "attributes": attributes,
            "derived_insights": derived_insights,
            "life_stories": life_stories,
            "behavioural_tendencies": behavioural_tendencies,
            "narrative": narrative,
            "demographic_anchor": demographic_anchor,
        }
        core_memory = self._assemble_core_memory(partial_record)

        working_memory = WorkingMemory(
            observations=[],
            reflections=[],
            plans=[],
            brand_memories={},
            simulation_state=SimulationState(
                current_turn=0,
                importance_accumulator=0.0,
                reflection_count=0,
                awareness_set={},
                consideration_set=[],
                last_decision=None,
            ),
        )

        memory = Memory(core=core_memory, working=working_memory)

        # decision_bullets — derived from objection_profile + key_tensions.
        # These are concise action-oriented bullets for downstream use
        # (e.g. sales enablement, survey design).
        decision_bullets = self._derive_decision_bullets(
            derived_insights=derived_insights,
            behavioural_tendencies=behavioural_tendencies,
        )

        # ---------------------------------------------------------------
        # Assemble PersonaRecord
        # ---------------------------------------------------------------
        persona = PersonaRecord(
            persona_id=persona_id,
            generated_at=datetime.now(tz=timezone.utc),
            generator_version=GENERATOR_VERSION,
            domain=icp_spec.domain,
            mode=icp_spec.mode,  # type: ignore[arg-type]
            demographic_anchor=demographic_anchor,
            life_stories=life_stories,
            attributes=attributes,
            derived_insights=derived_insights,
            behavioural_tendencies=behavioural_tendencies,
            narrative=narrative,
            decision_bullets=decision_bullets,
            memory=memory,
        )

        # ---------------------------------------------------------------
        # Step 6b — Replace inline core with authoritative assembly
        # assemble_core_memory() requires a PersonaRecord, so the inline
        # _assemble_core_memory() above bootstraps a valid PersonaRecord first;
        # this call then replaces it with the authoritative derivation from
        # src.memory.core_memory (OpenCode Sprint 3).
        # ---------------------------------------------------------------
        core_memory = assemble_core_memory(persona)
        persona = persona.model_copy(
            update={"memory": Memory(core=core_memory, working=working_memory)}
        )

        # ---------------------------------------------------------------
        # Step 7 — Validate
        # ---------------------------------------------------------------
        results = self.validator.validate_all(persona)
        failed = [r for r in results if not r.passed]
        if failed:
            details = "; ".join(
                f"{r.gate}: {', '.join(r.failures)}" for r in failed
            )
            raise ValueError(f"Persona validation failed — {details}")

        # ---------------------------------------------------------------
        # Step 7b — Bootstrap seed memories (simulation-ready mode only)
        # ---------------------------------------------------------------
        if icp_spec.mode == "simulation-ready":
            from src.memory.seed_memory import bootstrap_seed_memories
            seeded_working = bootstrap_seed_memories(
                core_memory=persona.memory.core,
                persona_name=persona.demographic_anchor.name,
            )
            persona = persona.model_copy(
                update={"memory": Memory(core=persona.memory.core, working=seeded_working)}
            )

        # ---------------------------------------------------------------
        # Step 8 — Return
        # ---------------------------------------------------------------
        return persona

    # ------------------------------------------------------------------
    # Step 6 helper — CoreMemory assembly
    # ------------------------------------------------------------------

    def _assemble_core_memory(self, partial_record: dict[str, Any]) -> CoreMemory:
        """Assemble CoreMemory from the constructed record fields.

        Field derivation:

        identity_statement
            First 25 words of narrative.first_person.  The opening of the
            first-person voice is the most concentrated self-description.

        key_values
            Assembled from primary_value_driver (anchor attribute, always
            present) plus the top 2 attributes by value within the 'values'
            category (highest continuous score = most strongly held value),
            deduplicated.  Result is 3–5 strings.

        life_defining_events
            Converted from life_stories.  LifeStory.when is parsed to an
            integer age; unresolvable values default to the persona's current
            age minus 10 (a neutral mid-life offset).

        relationship_map
            Assembled from trust_orientation.dominant and social attributes:
            - primary_decision_partner  → household structure hint
              (joint/nuclear/single-parent → partner, family, self)
            - key_influencers           → trust_orientation.dominant weight
              names at the top
            - trust_network             → top-weight trust types (score > 0.5)

        immutable_constraints
            - budget_ceiling       → income_bracket string from demographic anchor
            - non_negotiables      → derived from key_tensions (first 2 tensions,
                                     rephrased as "must have …" constraints)
            - absolute_avoidances  → empty list (no data source for this sprint;
                                     noted as a known gap)

        tendency_summary
            Direct copy of behavioural_tendencies.reasoning_prompt — spec §5
            says this field exists for context-window injection.
        """
        narrative = partial_record["narrative"]
        attributes: dict[str, dict] = partial_record["attributes"]
        life_stories = partial_record["life_stories"]
        behavioural_tendencies = partial_record["behavioural_tendencies"]
        derived_insights = partial_record["derived_insights"]
        demographic_anchor: DemographicAnchor = partial_record["demographic_anchor"]

        # --- identity_statement -------------------------------------------
        identity_statement = self._extract_first_n_words(
            narrative.first_person, _IDENTITY_STATEMENT_WORDS
        )

        # --- key_values ---------------------------------------------------
        key_values = self._derive_key_values(attributes, derived_insights)

        # --- life_defining_events -----------------------------------------
        life_defining_events = self._convert_life_stories(
            life_stories, demographic_anchor.age
        )

        # --- relationship_map ---------------------------------------------
        relationship_map = self._derive_relationship_map(
            demographic_anchor, behavioural_tendencies
        )

        # --- immutable_constraints ----------------------------------------
        immutable_constraints = self._derive_immutable_constraints(
            demographic_anchor, derived_insights
        )

        # --- tendency_summary ---------------------------------------------
        tendency_summary: str = behavioural_tendencies.reasoning_prompt

        return CoreMemory(
            identity_statement=identity_statement,
            key_values=key_values,
            life_defining_events=life_defining_events,
            relationship_map=relationship_map,
            immutable_constraints=immutable_constraints,
            tendency_summary=tendency_summary,
        )

    # ------------------------------------------------------------------
    # CoreMemory sub-helpers
    # ------------------------------------------------------------------

    def _extract_first_n_words(self, text: str, n: int) -> str:
        """Return the first n words of text, joined by spaces."""
        words = text.split()
        return " ".join(words[:n])

    def _derive_key_values(
        self,
        attributes: dict[str, dict],
        derived_insights: Any,
    ) -> list[str]:
        """Build a 3–5 item key_values list.

        Priority order:
        1. primary_value_driver (anchor attribute — always present as a string value)
        2. Top 2 highest continuous-valued attributes in the 'values' category,
           using their label strings.
        """
        values_category: dict[str, Any] = attributes.get("values", {})

        # 1. Primary value driver (categorical anchor attribute).
        primary_driver_attr = values_category.get("primary_value_driver")
        primary = (
            str(primary_driver_attr.value)
            if primary_driver_attr is not None
            else str(derived_insights.primary_value_orientation)
        )

        seen: set[str] = {primary}
        result: list[str] = [primary]

        # 2. Top 2 highest-score continuous attributes in 'values' category,
        #    excluding primary_value_driver.
        continuous_attrs = [
            (name, attr)
            for name, attr in values_category.items()
            if name != "primary_value_driver"
            and attr.type == "continuous"
            and isinstance(attr.value, float)
        ]
        continuous_attrs.sort(key=lambda t: t[1].value, reverse=True)

        for name, attr in continuous_attrs[:2]:
            label = attr.label if attr.label else name.replace("_", " ")
            if label not in seen:
                seen.add(label)
                result.append(label)

        # Pad to 3 items if we couldn't find enough values attributes.
        fallbacks = [
            str(derived_insights.trust_anchor),
            str(derived_insights.risk_appetite),
            str(derived_insights.decision_style),
        ]
        for fb in fallbacks:
            if len(result) >= 3:
                break
            if fb not in seen:
                seen.add(fb)
                result.append(fb)

        # Cap at 5 per CoreMemory validator.
        return result[:5]

    def _convert_life_stories(
        self,
        life_stories: list[Any],
        current_age: int,
    ) -> list[LifeDefiningEvent]:
        """Convert LifeStory objects to LifeDefiningEvent objects.

        LifeStory.when is free-form text such as "age 24", "at 18",
        "29 years old", or a year like "2015".  We parse to an integer age.
        If parsing fails, we default to current_age - 10.
        """
        events: list[LifeDefiningEvent] = []
        for story in life_stories:
            age_when = self._parse_age_from_when(story.when, current_age)
            events.append(
                LifeDefiningEvent(
                    age_when=age_when,
                    event=story.event,
                    lasting_impact=story.lasting_impact,
                )
            )
        return events

    def _parse_age_from_when(self, when_str: str, current_age: int) -> int:
        """Parse an integer age from a 'when' string.

        Accepted patterns (case-insensitive):
          "age 24", "at 24", "24 years old", "24"
        If the string is a 4-digit year (e.g. "2010"), we approximate age by
        subtracting the implied birth year.  If nothing parses, return
        current_age - 10 as a safe fallback.
        """
        if not when_str:
            return max(1, current_age - 10)

        s = when_str.strip().lower()

        # "age 24", "at 24", "24 years old"
        m = re.search(r"\b(\d{1,2})\b", s)
        if m:
            candidate = int(m.group(1))
            if 1 <= candidate <= 120:
                return candidate

        # 4-digit year: approximate via current date - current_age gives birth year,
        # then year - birth_year gives age at that year.
        m_year = re.search(r"\b(19\d{2}|20\d{2})\b", s)
        if m_year:
            year = int(m_year.group(1))
            birth_year = datetime.now(tz=timezone.utc).year - current_age
            age_at_event = year - birth_year
            if 1 <= age_at_event <= 120:
                return age_at_event

        return max(1, current_age - 10)

    def _derive_relationship_map(
        self,
        demographic_anchor: DemographicAnchor,
        behavioural_tendencies: Any,
    ) -> RelationshipMap:
        """Assemble RelationshipMap.

        primary_decision_partner
            Inferred from household structure:
            - 'joint'         → "family (joint household)"
            - 'nuclear'       → "partner / spouse"
            - 'single-parent' → "self"
            - 'couple-no-kids'→ "partner"
            - 'other'         → "self"

        key_influencers
            The top 2 trust weight types (sorted by weight descending) from
            trust_orientation.weights, expressed as named strings.

        trust_network
            All trust types with weight > 0.5 from trust_orientation.weights.
            At least one entry is guaranteed (the dominant type is always
            included as fallback).
        """
        structure = demographic_anchor.household.structure

        partner_map = {
            "joint": "family (joint household)",
            "nuclear": "partner / spouse",
            "single-parent": "self",
            "couple-no-kids": "partner",
            "other": "self",
        }
        primary_decision_partner = partner_map.get(structure, "self")

        weights = behavioural_tendencies.trust_orientation.weights
        weight_pairs = [
            ("expert", weights.expert),
            ("peer", weights.peer),
            ("brand", weights.brand),
            ("ad", weights.ad),
            ("community", weights.community),
            ("influencer", weights.influencer),
        ]
        weight_pairs_sorted = sorted(weight_pairs, key=lambda t: t[1], reverse=True)

        key_influencers = [name for name, _ in weight_pairs_sorted[:2]]

        trust_network = [name for name, w in weight_pairs_sorted if w > 0.5]
        if not trust_network:
            # Fallback: always include the dominant trust type.
            trust_network = [weight_pairs_sorted[0][0]]

        return RelationshipMap(
            primary_decision_partner=primary_decision_partner,
            key_influencers=key_influencers,
            trust_network=trust_network,
        )

    def _derive_immutable_constraints(
        self,
        demographic_anchor: DemographicAnchor,
        derived_insights: Any,
    ) -> ImmutableConstraints:
        """Assemble ImmutableConstraints.

        budget_ceiling
            Directly from demographic_anchor.household.income_bracket.
            This is the only data we have for an absolute spend limit at
            persona-creation time.

        non_negotiables
            Derived from the first 2 key_tensions (from derived_insights),
            rephrased as "must have …" requirement strings.  If fewer than
            2 tensions exist, the list may have 1 item.

        absolute_avoidances
            No structured data source is available for this sprint.  Set to
            an empty list.  This is a known gap — a future sprint can populate
            this from domain-specific taboo attributes.
        """
        budget_ceiling: str | None = demographic_anchor.household.income_bracket or None

        non_negotiables: list[str] = []
        for tension in derived_insights.key_tensions[:2]:
            # Rephrase: "X vs Y" → "Must resolve or manage: X vs Y"
            non_negotiables.append(f"Must manage: {tension}")

        absolute_avoidances: list[str] = []

        return ImmutableConstraints(
            budget_ceiling=budget_ceiling,
            non_negotiables=non_negotiables,
            absolute_avoidances=absolute_avoidances,
        )

    # ------------------------------------------------------------------
    # decision_bullets helper
    # ------------------------------------------------------------------

    def _derive_decision_bullets(
        self,
        derived_insights: Any,
        behavioural_tendencies: Any,
    ) -> list[str]:
        """Derive concise decision-relevant bullets for downstream use.

        Assembled from:
        - Primary objection types (from objection_profile), phrased as
          "Watch for: [type]" notes.
        - Key tensions (from derived_insights.key_tensions), phrased as
          "Tension: [tension]" notes.
        - Decision style framing.

        The spec lists decision_bullets as a required field but does not
        specify its derivation algorithm — this is the most principled
        rule-based approach given the available data.
        """
        bullets: list[str] = []

        # Decision style framing.
        bullets.append(
            f"Decision style: {derived_insights.decision_style} "
            f"(score {derived_insights.decision_style_score:.2f})"
        )

        # Primary value orientation.
        bullets.append(
            f"Primary value driver: {derived_insights.primary_value_orientation}"
        )

        # Risk appetite.
        bullets.append(f"Risk appetite: {derived_insights.risk_appetite}")

        # Objection profile — up to first 3 objections.
        for obj in behavioural_tendencies.objection_profile[:3]:
            bullets.append(
                f"Objection ({obj.likelihood} likelihood, {obj.severity}): "
                f"{obj.objection_type.replace('_', ' ')}"
            )

        # Key tensions — up to first 2.
        for tension in derived_insights.key_tensions[:2]:
            bullets.append(f"Tension: {tension}")

        return bullets

    # ------------------------------------------------------------------
    # Persona ID
    # ------------------------------------------------------------------

    def _make_persona_id(self, icp_spec: ICPSpec) -> str:
        """Format: pg-[prefix]-[NNN]  e.g. pg-cpg-001"""
        return f"pg-{icp_spec.persona_id_prefix}-{icp_spec.persona_index:03d}"

    # ------------------------------------------------------------------
    # Internal guard
    # ------------------------------------------------------------------

    def _assert_components_available(self) -> None:
        """Raise ImportError early if any Sprint 2 component is missing."""
        missing: list[str] = []
        if not _DERIVED_INSIGHTS_AVAILABLE:
            missing.append("src.generation.derived_insights.DerivedInsightsComputer")
        if not _LIFE_STORY_AVAILABLE:
            missing.append("src.generation.life_story_generator.LifeStoryGenerator")
        if not _TENDENCY_AVAILABLE:
            missing.append("src.generation.tendency_estimator.TendencyEstimator")
        if not _NARRATIVE_AVAILABLE:
            missing.append("src.generation.narrative_generator.NarrativeGenerator")
        if missing:
            raise ImportError(
                "IdentityConstructor.build() requires Sprint 2 components that are "
                "not yet installed.  Missing:\n"
                + "\n".join(f"  - {m}" for m in missing)
            )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = ["IdentityConstructor", "ICPSpec"]
