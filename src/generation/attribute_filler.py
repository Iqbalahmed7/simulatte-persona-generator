from __future__ import annotations
import asyncio
import json
import random
from typing import Dict, Any, List, Optional

from src.schema.persona import DemographicAnchor, Attribute
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

        # Step 1: Fill anchor attributes sequentially
        fill_order = self._get_fill_order(taxonomy, anchor_overrides or {})
        anchors = [attr_def for attr_def in fill_order if self._is_anchor(attr_def)]
        for attr_def in anchors:
            attr = await self._fill_single_attribute(attr_def, profile_so_far, demographic_anchor)
            self._add_to_attributes(attributes, attr_def.category, attr_def.name, attr)
            profile_so_far[attr_def.name] = attr.value
            self._apply_correlation_check(attr_def.name, attr.value, profile_so_far)

        # Step 2: Apply anchor overrides (if any)
        if anchor_overrides:
            for name, value in anchor_overrides.items():
                if name in TAXONOMY_BY_NAME:
                    attr_def = TAXONOMY_BY_NAME[name]
                    label = self._get_label(attr_def, value)
                    attr = Attribute(value=value, type=attr_def.attr_type, label=label, source="anchored")
                    self._add_to_attributes(attributes, attr_def.category, name, attr)
                    profile_so_far[name] = value
                    self._apply_correlation_check(name, value, profile_so_far)

        # Step 3: Fill extended (non-anchor) in batches of 10
        extended = [attr_def for attr_def in fill_order if not self._is_anchor(attr_def)]
        await self._fill_batched(attributes, extended, profile_so_far, demographic_anchor)

        # Step 4: Fill domain-specific sequentially (caller-provided)
        if domain_attrs:
            for attr_def in domain_attrs:
                attr = await self._fill_single_attribute(attr_def, profile_so_far, demographic_anchor)
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
                self._fill_single_attribute(attr_def, profile_so_far, demographic_anchor)
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
    ) -> Attribute:
        system_prompt = """You are assigning a single psychological or behavioural attribute for a persona.
Be realistic, specific, and consistent with everything already assigned."""

        recent_attrs = list(profile_so_far.items())[-15:]
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

        user_prompt = f"""Persona so far:
- Demographics: {demogs_str}
- Attributes assigned so far: {attrs_str}

Assign this attribute:
Name: {attr_def.name}
Category: {attr_def.category}
Description: {attr_def.description}
Type: {type_info}{prior_info}

Return JSON only: {{"value": ..., "label": "..."}}"""

        try:
            response = await api_call_with_retry(
                self.llm_client.messages.create,
                model=self.model,
                max_tokens=128,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw_text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1].lstrip("json").strip()
            parsed = json.loads(raw_text)
            value = parsed["value"]
            label = parsed.get("label", "medium")
            attr = Attribute(value=value, type=attr_def.attr_type, label=label, source="sampled")
            return attr
        except Exception:
            pass  # fall through to fallback

        # Fallback to prior
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
        return Attribute(value=fallback_value, type=attr_def.attr_type, label=fallback_label, source="sampled")

    def _get_fill_order(
        self, taxonomy: List[AttributeDefinition], anchor_overrides: Dict[str, Any]
    ) -> List[AttributeDefinition]:
        anchors = [
            d for d in taxonomy if d.anchor_order is not None and 1 <= d.anchor_order <= 8
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
        return {
            "age": anchor.age,
            "gender": anchor.gender,
            "location_urban_tier": anchor.location.urban_tier,
            "income_bracket": anchor.household.income_bracket,
            "life_stage": anchor.life_stage,
            "education": anchor.education,
            "employment": anchor.employment,
        }

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
        return attr_def.anchor_order is not None and 1 <= attr_def.anchor_order <= 8

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
