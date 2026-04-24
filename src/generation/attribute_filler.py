from __future__ import annotations
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal

from src.observability.cost_tracer import CostTracer, make_record, usage_to_token_counts
from src.schema.persona import (
    Attribute,
    AttributeProvenance,
    DemographicAnchor,
    GenerationStage,
)
from src.schema.worldview import WorldviewAnchor
from src.taxonomy.base_taxonomy import (
    AttributeDefinition,
    TAXONOMY_BY_NAME,
    KNOWN_CORRELATIONS,
    KNOWN_CORRELATIONS_DICT,
)
from src.utils.retry import api_call_with_retry


class AttributeFiller:
    def __init__(self, llm_client: Any, model: str = "claude-sonnet-4-6"):
        self.llm_client = llm_client
        self.model = model

    async def fill(
        self,
        demographic_anchor: DemographicAnchor,
        taxonomy: List[AttributeDefinition],
        anchor_overrides: Optional[Dict[str, Any]] = None,
        domain_attrs: Optional[List[AttributeDefinition]] = None,
    ) -> Dict[str, Dict[str, Attribute]]:
        """Asynchronously fills attributes progressively."""
        profile_so_far = self._demographics_to_profile(demographic_anchor)
        attributes: Dict[str, Dict[str, Attribute]] = {}

        # If a WorldviewAnchor is present, extract worldview taxonomy overrides.
        # These are injected as anchored values so no LLM call is needed for them.
        # Caller-supplied anchor_overrides take precedence over worldview-derived ones.
        effective_overrides: Dict[str, Any] = {}
        if demographic_anchor.worldview is not None:
            effective_overrides.update(
                _worldview_anchor_to_overrides(demographic_anchor.worldview)
            )
        if anchor_overrides:
            effective_overrides.update(anchor_overrides)

        # Step 1: Fill anchor attributes sequentially
        fill_order = self._get_fill_order(taxonomy, effective_overrides)
        anchors = [attr_def for attr_def in fill_order if self._is_anchor(attr_def)]
        for attr_def in anchors:
            # Worldview anchors (order 9-14): use pre-computed value if available
            if attr_def.name in effective_overrides and attr_def.anchor_order is not None and attr_def.anchor_order >= 9:
                value = effective_overrides[attr_def.name]
                label = self._get_label(attr_def, value)
                provenance = AttributeProvenance(
                    source_class="empirical",
                    source_detail="worldview_anchor",
                    confidence=1.0,
                    conditioned_by=[],
                    reasoning=None,
                    generation_stage="anchor",
                    filled_at=datetime.now(timezone.utc),
                )
                attr = Attribute(value=value, type=attr_def.attr_type, label=label, source="anchored", provenance=provenance)
            else:
                attr = await self._fill_single_attribute(attr_def, profile_so_far, demographic_anchor, generation_stage="anchor")
            self._add_to_attributes(attributes, attr_def.category, attr_def.name, attr)
            profile_so_far[attr_def.name] = attr.value
            self._apply_correlation_check(attr_def.name, attr.value, profile_so_far)

        # Step 2: Apply anchor overrides (if any)
        if effective_overrides:
            for name, value in effective_overrides.items():
                if name in TAXONOMY_BY_NAME:
                    attr_def = TAXONOMY_BY_NAME[name]
                    label = self._get_label(attr_def, value)
                    provenance = AttributeProvenance(
                        source_class="empirical",
                        source_detail="demographic_anchor",
                        confidence=1.0,
                        conditioned_by=[],
                        reasoning=None,
                        generation_stage="anchor",
                        filled_at=datetime.now(timezone.utc),
                    )
                    attr = Attribute(value=value, type=attr_def.attr_type, label=label, source="anchored", provenance=provenance)
                    self._add_to_attributes(attributes, attr_def.category, name, attr)
                    profile_so_far[name] = value
                    self._apply_correlation_check(name, value, profile_so_far)

        # Step 3: Fill extended (non-anchor) in batches of 10
        extended = [attr_def for attr_def in fill_order if not self._is_anchor(attr_def)]
        await self._fill_batched(attributes, extended, profile_so_far, demographic_anchor)

        # Step 4: Fill domain-specific sequentially (caller-provided)
        if domain_attrs:
            for attr_def in domain_attrs:
                attr = await self._fill_single_attribute(attr_def, profile_so_far, demographic_anchor, generation_stage="domain_specific")
                self._add_to_attributes(attributes, attr_def.category, attr_def.name, attr)
                profile_so_far[attr_def.name] = attr.value
                self._apply_correlation_check(attr_def.name, attr.value, profile_so_far)

        return attributes

    async def _fill_batched(
        self,
        attributes: Dict[str, Dict[str, Attribute]],
        batch_defs: List[AttributeDefinition],
        profile_so_far: Dict[str, Any],
        demographic_anchor: DemographicAnchor,
    ) -> None:
        batch_size = 10
        for i in range(0, len(batch_defs), batch_size):
            batch = batch_defs[i : i + batch_size]
            tasks = [
                self._fill_single_attribute(attr_def, profile_so_far, demographic_anchor, generation_stage="extended")
                for attr_def in batch
            ]
            batch_attrs = await asyncio.gather(*tasks)
            for attr_def, attr in zip(batch, batch_attrs):
                self._add_to_attributes(attributes, attr_def.category, attr_def.name, attr)
                profile_so_far[attr_def.name] = attr.value
                self._apply_correlation_check(attr_def.name, attr.value, profile_so_far)

    async def _fill_single_attribute(
        self,
        attr_def: AttributeDefinition,
        profile_so_far: Dict[str, Any],
        demographic_anchor: DemographicAnchor,
        generation_stage: GenerationStage = "extended",
    ) -> Attribute:
        CostTracer.set_phase("attribute_fill")
        # Sparsity prior (DeepPersona §2): prevent rare trait combinations from
        # being zero-probability. 20% of the time, inject a prompt nudge that
        # encourages non-modal (surprising but plausible) attribute values.
        # This counteracts LLM homogeneity bias documented across all persona
        # generation research (Master Spec §2: "Known failures to guard against").
        # The nudge is seeded per attr_name + persona name for reproducibility.
        sparsity_seed = hash(f"{attr_def.name}:{demographic_anchor.name}")
        apply_sparsity = (sparsity_seed % 5) == 0  # ~20% of attributes

        sparsity_nudge = ""
        if apply_sparsity:
            sparsity_nudge = (
                "\n\nIMPORTANT — sparsity prior: For this attribute, consider assigning "
                "a value that is SURPRISING but PLAUSIBLE given this persona's profile. "
                "Real people are not perfectly predictable — sometimes analytical people "
                "make gut decisions, sometimes frugal people splurge, sometimes introverts "
                "are socially bold. If there is a non-obvious but defensible value, prefer it. "
                "Do NOT assign the most predictable/modal value."
            )

        system_prompt = (
            "You are assigning a single psychological or behavioural attribute for a persona.\n"
            "Be realistic, specific, and consistent with everything already assigned."
            + sparsity_nudge
        )

        recent_attrs = list(profile_so_far.items())[-15:]
        context_attr_names = [k for k, _ in recent_attrs]
        attrs_str = "\n".join(f"- {k}: {v}" for k, v in recent_attrs)

        demogs = {
            "age": demographic_anchor.age,
            "gender": demographic_anchor.gender,
            "location_urban_tier": demographic_anchor.location.urban_tier,
            "income_bracket": demographic_anchor.household.income_bracket,
            "life_stage": demographic_anchor.life_stage,
        }
        demogs_str = ", ".join(f"{k}={v}" for k, v in demogs.items())

        type_info = f"{attr_def.attr_type}"
        if attr_def.attr_type == "continuous":
            type_info += " (0.0-1.0)"
        elif attr_def.attr_type == "categorical" and attr_def.options:
            type_info += f" (options: {attr_def.options})"

        prior_info = ""
        if attr_def.population_prior is not None:
            prior_info = f"\nPopulation prior: {attr_def.population_prior}"

        available_ctx = ", ".join(context_attr_names) if context_attr_names else "none"

        user_prompt = f"""Persona so far:
- Demographics: {demogs_str}
- Attributes assigned so far: {attrs_str}

Assign this attribute:
Name: {attr_def.name}
Category: {attr_def.category}
Description: {attr_def.description}
Type: {type_info}{prior_info}

Available context attributes: [{available_ctx}]

Return JSON only:
{{
  "value": ...,
  "label": "...",
  "confidence": <float 0.0-1.0 reflecting certainty of this assignment>,
  "reasoning": "<1-2 sentence explanation of why this value fits this persona>",
  "key_influences": ["<attr_name>", ...]  // 2-5 attributes from context that most shaped this value; empty list if none
}}"""

        started = time.monotonic()
        status: Literal["ok", "retry", "fail"] = "ok"
        input_tokens = 0
        output_tokens = 0
        model_name = str(getattr(self.llm_client, "model_name", None) or self.model)
        filled_at = datetime.now(timezone.utc)
        try:
            response = await api_call_with_retry(
                self.llm_client.messages.create,
                model=self.model,
                max_tokens=300,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_prompt}],
            )
            input_tokens, output_tokens = usage_to_token_counts(
                getattr(response, "usage", None)
            )
            raw_text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1].lstrip("json").strip()
            parsed = json.loads(raw_text)
            value = parsed["value"]
            label = parsed.get("label", "medium")

            # Build provenance from LLM-reported fields (all optional with safe defaults)
            raw_confidence = parsed.get("confidence", 0.7)
            confidence = float(raw_confidence) if isinstance(raw_confidence, (int, float)) else 0.7
            confidence = max(0.0, min(1.0, confidence))

            raw_influences = parsed.get("key_influences", [])
            # Validate reported influences are actually in context (prevent hallucination)
            valid_influences = [
                k for k in (raw_influences if isinstance(raw_influences, list) else [])
                if k in context_attr_names
            ]

            provenance = AttributeProvenance(
                source_class="inferred",
                source_detail=f"llm_inference_{model_name}",
                confidence=confidence,
                conditioned_by=valid_influences,
                reasoning=parsed.get("reasoning") or None,
                generation_stage=generation_stage,
                filled_at=filled_at,
            )
            attr = Attribute(value=value, type=attr_def.attr_type, label=label, source="sampled", provenance=provenance)
            return attr
        except Exception:
            status = "fail"
        finally:
            CostTracer.record(
                make_record(
                    sub_step=attr_def.name,
                    model=model_name,
                    started_monotonic=started,
                    status=status,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )

        # Fallback to prior — provenance records this as a degraded fill
        fallback_provenance = AttributeProvenance(
            source_class="inferred",
            source_detail=f"fallback_prior_{model_name}",
            confidence=0.1,
            conditioned_by=[],
            reasoning="LLM call failed; value derived from population prior.",
            generation_stage=generation_stage,
            filled_at=datetime.now(timezone.utc),
        )
        if attr_def.attr_type == "categorical":
            # Categorical fallback: pick first option or "unknown"
            fallback_value = attr_def.options[0] if attr_def.options else "unknown"
            fallback_label = str(fallback_value)
        else:
            raw_prior = attr_def.population_prior
            # Domain templates (e.g. CPG) convert population_prior to a dict
            # {"value": float, "label": str} — extract the float if so
            if isinstance(raw_prior, dict):
                fallback_value = float(raw_prior.get("value", 0.5))
                fallback_label = str(raw_prior.get("label", "medium"))
            else:
                fallback_value = float(raw_prior) if raw_prior is not None else 0.5
                fallback_label = "medium"
        return Attribute(value=fallback_value, type=attr_def.attr_type, label=fallback_label, source="sampled", provenance=fallback_provenance)

    def _get_fill_order(
        self, taxonomy: List[AttributeDefinition], anchor_overrides: Dict[str, Any]
    ) -> List[AttributeDefinition]:
        # Anchors 1-8 are core persona anchors; 9-14 are worldview anchors (ARCH-001).
        anchors = [
            d for d in taxonomy if d.anchor_order is not None and 1 <= d.anchor_order <= 14
        ]
        anchors.sort(key=lambda d: d.anchor_order)

        override_defs = []
        for name in anchor_overrides:
            if name in TAXONOMY_BY_NAME:
                override_defs.append(TAXONOMY_BY_NAME[name])

        remaining = [d for d in taxonomy if d not in anchors and d.name not in anchor_overrides]
        cat_groups: Dict[str, List[AttributeDefinition]] = {}
        for d in remaining:
            cat_groups.setdefault(d.category, []).append(d)
        randomized = []
        for group in cat_groups.values():
            random.shuffle(group)
            randomized.extend(group)

        return anchors + override_defs + randomized

    def _demographics_to_profile(self, anchor: DemographicAnchor) -> Dict[str, Any]:
        profile: Dict[str, Any] = {
            "age": anchor.age,
            "gender": anchor.gender,
            "country": anchor.location.country,
            "location_urban_tier": anchor.location.urban_tier,
            "income_bracket": anchor.household.income_bracket,
            "life_stage": anchor.life_stage,
            "education": anchor.education,
            "employment": anchor.employment,
        }
        # Inject worldview context when present so the LLM has it for all fills.
        if anchor.worldview is not None:
            wv = anchor.worldview
            profile["worldview_institutional_trust"] = wv.institutional_trust
            profile["worldview_social_change_pace"] = wv.social_change_pace
            profile["worldview_collectivism"] = wv.collectivism_score
            profile["worldview_econ_security_priority"] = wv.economic_security_priority
            if wv.political_profile is not None:
                profile["political_archetype"] = wv.political_profile.archetype
                profile["political_archetype_desc"] = wv.political_profile.description[:80]
        return profile

    def _add_to_attributes(
        self,
        attributes: Dict[str, Dict[str, Attribute]],
        category: str,
        name: str,
        attr: Attribute,
    ) -> None:
        if category not in attributes:
            attributes[category] = {}
        attributes[category][name] = attr

    def _get_label(self, attr_def: AttributeDefinition, value: Any) -> str:
        if attr_def.attr_type == "categorical":
            return str(value)
        v = float(value)
        if v > 0.66:
            return "high"
        elif v > 0.33:
            return "medium"
        return "low"

    def _is_anchor(self, attr_def: AttributeDefinition) -> bool:
        # Anchors 1-8: core persona anchors. Anchors 9-14: worldview anchors (ARCH-001).
        return attr_def.anchor_order is not None and 1 <= attr_def.anchor_order <= 14

    def _apply_correlation_check(
        self, newly_assigned: str, newly_assigned_value: Any, profile_so_far: Dict[str, Any]
    ) -> None:
        """Soft correlation check — logs tensions for constraint_checker."""
        corrs = KNOWN_CORRELATIONS_DICT.get(newly_assigned, [])
        for other_attr, direction in corrs:
            if other_attr in profile_so_far:
                other_val = profile_so_far[other_attr]
                new_v = float(newly_assigned_value) if isinstance(newly_assigned_value, (int, float)) else 0.5
                other_v = float(other_val) if isinstance(other_val, (int, float)) else 0.5
                if direction == "positive":
                    if (new_v > 0.7 and other_v < 0.3) or (new_v < 0.3 and other_v > 0.7):
                        print(f"⚠️ Correlation tension (positive): {newly_assigned}({new_v:.2f}) vs {other_attr}({other_v:.2f})")
                elif direction == "negative":
                    if (new_v > 0.7 and other_v > 0.7) or (new_v < 0.3 and other_v < 0.3):
                        print(f"⚠️ Correlation tension (negative): {newly_assigned}({new_v:.2f}) vs {other_attr}({other_v:.2f})")


# ---------------------------------------------------------------------------
# Module-level helper — WorldviewAnchor → taxonomy attribute overrides
# ---------------------------------------------------------------------------

# Maps sub-archetypes to their core spectrum equivalent for the political_lean
# taxonomy attribute (which uses the 5-value core spectrum only).
_ARCHETYPE_TO_LEAN: Dict[str, str] = {
    "conservative":           "conservative",
    "lean_conservative":      "lean_conservative",
    "moderate":               "moderate",
    "lean_progressive":       "lean_progressive",
    "progressive":            "progressive",
    # Sub-archetypes → nearest core spectrum value
    "religious_conservative": "conservative",
    "fiscal_conservative":    "lean_conservative",
    "working_class_populist": "lean_conservative",
    "college_educated_liberal": "progressive",
    "non_voter_disengaged":   "moderate",
}


def _worldview_anchor_to_overrides(worldview: WorldviewAnchor) -> Dict[str, Any]:
    """Derive worldview taxonomy attribute values from a WorldviewAnchor.

    Returns a dict of {attr_name: value} suitable for use as anchor_overrides
    in AttributeFiller.fill(). All 6 worldview taxonomy attributes are populated:

      political_lean              ← political_profile.archetype (mapped to core 5)
      economic_philosophy         ← economic_security_priority (thresholded)
      social_change_pace          ← social_change_pace (direct)
      institutional_trust_govt    ← institutional_trust (base)
      institutional_trust_media   ← institutional_trust − 0.07 (media typically lower)
      institutional_trust_science ← institutional_trust + 0.10 (science typically higher)

    The science/media offsets reflect consistent findings from Pew trust surveys:
    science trust runs ~10pp above general institutional trust on average;
    media trust runs ~7pp below.
    """
    overrides: Dict[str, Any] = {}

    it = worldview.institutional_trust
    overrides["social_change_pace"] = worldview.social_change_pace
    overrides["institutional_trust_government"] = round(it, 2)
    overrides["institutional_trust_media"] = round(max(0.0, min(1.0, it - 0.07)), 2)
    overrides["institutional_trust_science"] = round(max(0.0, min(1.0, it + 0.10)), 2)

    # economic_security_priority → economic_philosophy categorical
    esp = worldview.economic_security_priority
    if esp >= 0.65:
        overrides["economic_philosophy"] = "interventionist"
    elif esp >= 0.35:
        overrides["economic_philosophy"] = "mixed"
    else:
        overrides["economic_philosophy"] = "free_market"

    # political_profile.archetype → political_lean (core 5-value spectrum)
    if worldview.political_profile is not None:
        lean = _ARCHETYPE_TO_LEAN.get(worldview.political_profile.archetype, "moderate")
        overrides["political_lean"] = lean

    # religious_salience → direct mapping when present on WorldviewAnchor
    if worldview.religious_salience is not None:
        overrides["religious_salience"] = round(worldview.religious_salience, 2)

    return overrides
