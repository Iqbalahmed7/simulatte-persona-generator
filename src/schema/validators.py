from __future__ import annotations

import re

from src.generation.constraint_checker import ConstraintChecker
from src.schema.persona import PersonaRecord, WorkingMemory
from src.taxonomy.base_taxonomy import AttributeDefinition

# Parallel sprint safety: these modules are built by OpenCode and Codex in Sprint 5.
# Wrap imports in try/except so validators.py remains importable even when they are absent.
try:
    from src.cohort.diversity_checker import check_diversity
except ImportError:
    check_diversity = None  # type: ignore[assignment]

try:
    from src.cohort.distinctiveness import check_distinctiveness
except ImportError:
    check_distinctiveness = None  # type: ignore[assignment]

try:
    from src.cohort.type_coverage import check_type_coverage
except ImportError:
    check_type_coverage = None  # type: ignore[assignment]


class ValidationResult:
    def __init__(
        self,
        passed: bool,
        gate: str,
        failures: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        self.passed = passed
        self.gate = gate
        self.failures = failures or []
        self.warnings = warnings or []

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "gate": self.gate,
            "failures": self.failures,
            "warnings": self.warnings,
        }


class PersonaValidator:
    """
    Runs structural validation gates G1, G2, G3 on a persona record.
    """

    def __init__(self):
        self.constraint_checker = ConstraintChecker()

    def validate_all(
        self,
        persona: PersonaRecord,
        include_narrative: bool = False,
        include_memory: bool = False,
    ) -> list[ValidationResult]:
        """
        G1, G2, G3 always.
        G4, G5 when include_narrative=True.
        G10 when include_memory=True (passes persona.memory.working to g10_seed_memory_count).
        """
        results = [
            self.g1_schema_validity(persona),
            self.g2_hard_constraints(persona),
            # Note: G3 requires the full taxonomy list for reference if needed,
            # but the rules TR1-TR8 specify category/name directly.
            self.g3_tendency_attribute_consistency(persona),
        ]
        if include_narrative:
            results.append(self.g4_narrative_completeness(persona))
            results.append(self.g5_narrative_attribute_alignment(persona))
        if include_memory:
            results.append(self.g10_seed_memory_count(persona.memory.working))
        return results

    def g1_schema_validity(self, persona: PersonaRecord) -> ValidationResult:
        """
        G1: Structural validation of the persona record.
        """
        failures: list[str] = []

        # key_tensions has ≥ 1 item (already checked by Pydantic, but let's be explicit)
        if len(persona.derived_insights.key_tensions) < 1:
            failures.append("G1: key_tensions must have ≥ 1 item")

        # life_stories has 2–3 items (checked by Pydantic)
        if not (2 <= len(persona.life_stories) <= 3):
            failures.append("G1: life_stories must have 2–3 items")

        # key_values has 3–5 items (checked by Pydantic)
        if not (3 <= len(persona.memory.core.key_values) <= 5):
            failures.append("G1: key_values must have 3–5 items")

        # source_observation_ids on every Reflection has ≥ 2 items (checked by Pydantic)
        for i, reflection in enumerate(persona.memory.working.reflections):
            if len(reflection.source_observation_ids) < 2:
                failures.append(f"G1: Reflection {i} source_observation_ids must have ≥ 2 items")

        # All TrustWeights floats are 0.0–1.0 (checked by Pydantic)
        tw = persona.behavioural_tendencies.trust_orientation.weights
        for attr in ["expert", "peer", "brand", "ad", "community", "influencer"]:
            val = getattr(tw, attr)
            if not (0.0 <= val <= 1.0):
                failures.append(f"G1: TrustWeight {attr} is outside 0.0-1.0: {val}")

        # All Attribute sources are from the valid set (checked by Pydantic)
        # (AttributeSource is a Literal, Pydantic already enforces this)
        
        # persona_id matches format pg-[prefix]-[NNN]
        if not re.match(r"^pg-[a-zA-Z0-9_]+-\d+$", persona.persona_id):
            failures.append(f"G1: persona_id {persona.persona_id} does not match format pg-[prefix]-[NNN]")

        return ValidationResult(passed=len(failures) == 0, gate="G1", failures=failures)

    def g2_hard_constraints(self, persona: PersonaRecord) -> ValidationResult:
        """
        G2: Rejects all impossible combinations (HC1–HC6).
        """
        violations = self.constraint_checker.check_hard_constraints(persona)
        failures = [v.description for v in violations]
        return ValidationResult(passed=len(failures) == 0, gate="G2", failures=failures)

    def g3_tendency_attribute_consistency(
        self,
        persona: PersonaRecord,
        taxonomy: list[AttributeDefinition] | None = None,
    ) -> ValidationResult:
        """
        G3: Flags all 8 tendency-attribute rule violations (TR1–TR8).
        If an attribute needed for a check is missing (returns None), the check is
        skipped silently — a missing attribute cannot violate a rule.
        """
        failures: list[str] = []

        bt = persona.behavioural_tendencies

        # TR1: budget_consciousness > 0.70 → price_sensitivity.band must be "high" or "extreme"
        val = self._get_attr_value(persona, "values", "budget_consciousness")
        if (
            isinstance(val, (int, float))
            and val > 0.70
            and bt.price_sensitivity.band not in ("high", "extreme")
        ):
            failures.append(
                "G3: TR1 violation: budget_consciousness > 0.70 requires "
                f"price_sensitivity.band 'high' or 'extreme' (got '{bt.price_sensitivity.band}')"
            )

        # TR2: budget_consciousness < 0.35 → price_sensitivity.band must be "low" or "medium"
        val = self._get_attr_value(persona, "values", "budget_consciousness")
        if (
            isinstance(val, (int, float))
            and val < 0.35
            and bt.price_sensitivity.band not in ("low", "medium")
        ):
            failures.append(
                "G3: TR2 violation: budget_consciousness < 0.35 requires "
                f"price_sensitivity.band 'low' or 'medium' (got '{bt.price_sensitivity.band}')"
            )

        # TR3: brand_loyalty > 0.70 → switching_propensity.band must be "low"
        val = self._get_attr_value(persona, "values", "brand_loyalty")
        if (
            isinstance(val, (int, float))
            and val > 0.70
            and bt.switching_propensity.band != "low"
        ):
            failures.append(
                "G3: TR3 violation: brand_loyalty > 0.70 requires "
                f"switching_propensity.band 'low' (got '{bt.switching_propensity.band}')"
            )

        # TR4: social_proof_bias > 0.65 → trust_orientation.weights.peer >= 0.65
        val = self._get_attr_value(persona, "social", "social_proof_bias")
        if (
            isinstance(val, (int, float))
            and val > 0.65
            and bt.trust_orientation.weights.peer < 0.65
        ):
            failures.append(
                "G3: TR4 violation: social_proof_bias > 0.65 requires "
                f"trust_orientation.weights.peer >= 0.65 (got {bt.trust_orientation.weights.peer:.2f})"
            )

        # TR5: authority_bias > 0.65 → trust_orientation.weights.expert >= 0.65
        val = self._get_attr_value(persona, "social", "authority_bias")
        if (
            isinstance(val, (int, float))
            and val > 0.65
            and bt.trust_orientation.weights.expert < 0.65
        ):
            failures.append(
                "G3: TR5 violation: authority_bias > 0.65 requires "
                f"trust_orientation.weights.expert >= 0.65 (got {bt.trust_orientation.weights.expert:.2f})"
            )

        # TR6: ad_receptivity < 0.30 → trust_orientation.weights.ad <= 0.25
        val = self._get_attr_value(persona, "lifestyle", "ad_receptivity")
        if (
            isinstance(val, (int, float))
            and val < 0.30
            and bt.trust_orientation.weights.ad > 0.25
        ):
            failures.append(
                "G3: TR6 violation: ad_receptivity < 0.30 requires "
                f"trust_orientation.weights.ad <= 0.25 (got {bt.trust_orientation.weights.ad:.2f})"
            )

        # TR7: information_need > 0.70 → objection_profile must include type "need_more_information"
        val = self._get_attr_value(persona, "psychology", "information_need")
        if (
            isinstance(val, (int, float))
            and val > 0.70
            and not any(
                o.objection_type == "need_more_information"
                for o in bt.objection_profile
            )
        ):
            failures.append(
                "G3: TR7 violation: information_need > 0.70 requires an objection of "
                "type 'need_more_information' in objection_profile"
            )

        # TR8: risk_tolerance < 0.30 → objection_profile must include type "risk_aversion"
        val = self._get_attr_value(persona, "psychology", "risk_tolerance")
        if (
            isinstance(val, (int, float))
            and val < 0.30
            and not any(
                o.objection_type == "risk_aversion"
                for o in bt.objection_profile
            )
        ):
            failures.append(
                "G3: TR8 violation: risk_tolerance < 0.30 requires an objection of "
                "type 'risk_aversion' in objection_profile"
            )

        return ValidationResult(passed=len(failures) == 0, gate="G3", failures=failures)

    def g4_narrative_completeness(self, persona: PersonaRecord) -> ValidationResult:
        """
        G4: 100% narrative completeness on sample personas.

        Checks:
        - narrative.first_person is non-empty and >= 50 words
        - narrative.third_person is non-empty and >= 80 words
        - narrative.display_name is non-empty
        - life_stories has 2-3 items (already checked in G1, recheck here for completeness)
        - Each life_story has non-empty title, when, event, lasting_impact
        - decision_bullets is non-empty (>= 1 item)
        - memory.core.identity_statement is non-empty and >= 10 words
        - memory.core.tendency_summary is non-empty and >= 20 words
        """
        failures: list[str] = []

        # narrative.first_person: non-empty and >= 50 words
        fp = persona.narrative.first_person
        if not fp or not fp.strip():
            failures.append("G4: narrative.first_person is empty")
        elif len(fp.split()) < 50:
            failures.append(
                f"G4: narrative.first_person has {len(fp.split())} words (minimum 50)"
            )

        # narrative.third_person: non-empty and >= 80 words
        tp = persona.narrative.third_person
        if not tp or not tp.strip():
            failures.append("G4: narrative.third_person is empty")
        elif len(tp.split()) < 80:
            failures.append(
                f"G4: narrative.third_person has {len(tp.split())} words (minimum 80)"
            )

        # narrative.display_name: non-empty
        if not persona.narrative.display_name or not persona.narrative.display_name.strip():
            failures.append("G4: narrative.display_name is empty")

        # life_stories: 2-3 items
        if not (2 <= len(persona.life_stories) <= 3):
            failures.append(
                f"G4: life_stories has {len(persona.life_stories)} items (must be 2-3)"
            )

        # Each life_story: non-empty title, when, event, lasting_impact
        for i, story in enumerate(persona.life_stories):
            for field_name, field_val in [
                ("title", story.title),
                ("when", story.when),
                ("event", story.event),
                ("lasting_impact", story.lasting_impact),
            ]:
                if not field_val or not field_val.strip():
                    failures.append(
                        f"G4: life_stories[{i}].{field_name} is empty"
                    )

        # decision_bullets: non-empty (>= 1 item)
        if not persona.decision_bullets:
            failures.append("G4: decision_bullets is empty (minimum 1 item required)")

        # memory.core.identity_statement: non-empty and >= 10 words
        id_stmt = persona.memory.core.identity_statement
        if not id_stmt or not id_stmt.strip():
            failures.append("G4: memory.core.identity_statement is empty")
        elif len(id_stmt.split()) < 10:
            failures.append(
                f"G4: memory.core.identity_statement has {len(id_stmt.split())} words (minimum 10)"
            )

        # memory.core.tendency_summary: non-empty and >= 20 words
        ts = persona.memory.core.tendency_summary
        if not ts or not ts.strip():
            failures.append("G4: memory.core.tendency_summary is empty")
        elif len(ts.split()) < 20:
            failures.append(
                f"G4: memory.core.tendency_summary has {len(ts.split())} words (minimum 20)"
            )

        return ValidationResult(passed=len(failures) == 0, gate="G4", failures=failures)

    def g5_narrative_attribute_alignment(self, persona: PersonaRecord) -> ValidationResult:
        """
        G5: 0 narrative-attribute contradictions on sample personas.

        Checks for detectable contradictions between narrative text and attribute values.
        Uses keyword scanning — not LLM-based (deterministic only).

        Rules:
        - If brand_loyalty > 0.80: narrative must NOT contain brand-agnostic phrases
        - If switching_propensity.band == "low": narrative must NOT contain high-switching phrases
        - If price_sensitivity.band in ("high", "extreme"): narrative must NOT contain
          price-indifferent phrases
        - If trust_orientation.dominant == "self": narrative must NOT contain
          social-conformity phrases
        - If risk_appetite == "low": narrative must NOT contain risk-embracing phrases

        Check both first_person and third_person narrative. Case-insensitive matching.
        """
        failures: list[str] = []

        # Combine both narrative fields for scanning
        combined_narrative = (
            persona.narrative.first_person + " " + persona.narrative.third_person
        ).lower()

        bt = persona.behavioural_tendencies

        # Rule 1: brand_loyalty > 0.80 → no brand-agnostic phrases
        brand_loyalty_val = self._get_attr_value(persona, "values", "brand_loyalty")
        if isinstance(brand_loyalty_val, (int, float)) and brand_loyalty_val > 0.80:
            contradicting_phrases = [
                "brand agnostic",
                "no brand preference",
                "doesn't care about brands",
                "does not care about brands",
                "any brand",
            ]
            for phrase in contradicting_phrases:
                if phrase in combined_narrative:
                    failures.append(
                        f"G5: brand_loyalty={brand_loyalty_val:.2f} (>0.80) but narrative "
                        f"contains brand-agnostic phrase: \"{phrase}\""
                    )

        # Rule 2: switching_propensity.band == "low" → no high-switching phrases
        if bt.switching_propensity.band == "low":
            contradicting_phrases = [
                "loves trying new brands",
                "always exploring",
                "frequent switcher",
                "brand hopper",
            ]
            for phrase in contradicting_phrases:
                if phrase in combined_narrative:
                    failures.append(
                        f"G5: switching_propensity.band='low' but narrative contains "
                        f"high-switching phrase: \"{phrase}\""
                    )

        # Rule 3: price_sensitivity.band in ("high", "extreme") → no price-indifferent phrases
        if bt.price_sensitivity.band in ("high", "extreme"):
            contradicting_phrases = [
                "money is no object",
                "price doesn't matter",
                "price does not matter",
                "never looks at price",
            ]
            for phrase in contradicting_phrases:
                if phrase in combined_narrative:
                    failures.append(
                        f"G5: price_sensitivity.band='{bt.price_sensitivity.band}' but narrative "
                        f"contains price-indifferent phrase: \"{phrase}\""
                    )

        # Rule 4: trust_orientation.dominant == "self" → no social-conformity phrases
        if bt.trust_orientation.dominant == "self":
            contradicting_phrases = [
                "follows the crowd",
                "does what others do",
                "easily influenced",
            ]
            for phrase in contradicting_phrases:
                if phrase in combined_narrative:
                    failures.append(
                        f"G5: trust_orientation.dominant='self' but narrative contains "
                        f"social-conformity phrase: \"{phrase}\""
                    )

        # Rule 5: risk_appetite == "low" → no risk-embracing phrases
        _NEGATION_PREFIXES = (
            "rarely", "never", "not ", "doesn't", "don't", "avoids",
            "seldom", "hardly", "won't", "cannot", "can't", "less",
            "nothing", "almost nothing",
        )

        def _phrase_is_negated(text: str, phrase: str) -> bool:
            """Return True if every occurrence of phrase is preceded by a negation word."""
            idx = 0
            found_unnegated = False
            while True:
                pos = text.find(phrase, idx)
                if pos == -1:
                    break
                # Look back up to 40 characters for a negation prefix
                window = text[max(0, pos - 40): pos]
                if not any(neg in window for neg in _NEGATION_PREFIXES):
                    found_unnegated = True
                    break
                idx = pos + 1
            return not found_unnegated

        risk_appetite_val = persona.derived_insights.risk_appetite
        if risk_appetite_val == "low":
            contradicting_phrases = [
                "thrill-seeker",
                "thrill seeker",
                "loves risk",
                "takes bold bets",
                "impulsive",
            ]
            for phrase in contradicting_phrases:
                if phrase in combined_narrative and not _phrase_is_negated(combined_narrative, phrase):
                    failures.append(
                        f"G5: risk_appetite='low' but narrative contains "
                        f"risk-embracing phrase: \"{phrase}\""
                    )

        return ValidationResult(passed=len(failures) == 0, gate="G5", failures=failures)

    def g10_seed_memory_count(self, memory: WorkingMemory) -> ValidationResult:
        """
        G10: >= 3 seed memories per persona after bootstrap.

        Checks:
        - memory.observations has >= 3 entries
        - All entries have valid id (non-empty string)
        - All entries have importance 1-10
        - All entries have emotional_valence -1.0 to 1.0
        - No duplicate ids
        """
        failures: list[str] = []

        obs = memory.observations

        # Must have at least 3 observations
        if len(obs) < 3:
            failures.append(
                f"G10: working memory has {len(obs)} observation(s); minimum is 3 seed memories"
            )

        # Validate each observation's fields
        for i, entry in enumerate(obs):
            # id must be a non-empty string
            if not isinstance(entry.id, str) or not entry.id.strip():
                failures.append(f"G10: observation[{i}] has invalid id (empty or non-string)")

            # importance must be 1–10 (Pydantic enforces this, but belt-and-suspenders)
            if not (1 <= entry.importance <= 10):
                failures.append(
                    f"G10: observation[{i}] importance={entry.importance} is outside 1–10"
                )

            # emotional_valence must be -1.0 to 1.0 (Pydantic enforces, belt-and-suspenders)
            if not (-1.0 <= entry.emotional_valence <= 1.0):
                failures.append(
                    f"G10: observation[{i}] emotional_valence={entry.emotional_valence} "
                    "is outside -1.0 to 1.0"
                )

        # No duplicate ids
        all_ids = [entry.id for entry in obs]
        seen: set[str] = set()
        for obs_id in all_ids:
            if obs_id in seen:
                failures.append(f"G10: duplicate observation id '{obs_id}'")
            seen.add(obs_id)

        return ValidationResult(passed=len(failures) == 0, gate="G10", failures=failures)

    def _get_attr_value(
        self,
        persona: PersonaRecord,
        category: str,
        name: str,
    ) -> float | str | None:
        """
        Safe accessor for persona.attributes[category][name].value.
        Returns None if missing.
        """
        try:
            return persona.attributes[category][name].value
        except KeyError:
            # Should log warning but the brief doesn't specify logger.
            return None


class CohortGateRunner:
    """Runs all cohort-level validation gates (G6, G7, G8, G9, G11)."""

    def run_all(
        self,
        personas: list[PersonaRecord],
    ) -> list[ValidationResult]:
        """
        Runs G6, G7, G8, G9, G11 in order.
        Returns list of ValidationResult (one per gate).
        """
        return [
            self.g6_distribution(personas),
            self.g7_distinctiveness(personas),
            self.g8_type_coverage(personas),
            self.g9_tension_completeness(personas),
            self.g11_tendency_source(personas),
        ]

    def g6_distribution(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G6: No city >20%, no age bracket >40%, income spans >=3 brackets."""
        if check_diversity is None:
            return ValidationResult(
                passed=True,
                gate="G6",
                warnings=["check_diversity not available (parallel sprint)"],
            )
        result = check_diversity(personas)
        return ValidationResult(
            gate="G6",
            passed=result.passed,
            failures=result.failures,
            warnings=result.warnings,
        )

    def g7_distinctiveness(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G7: Mean pairwise cosine distance on 8 core attributes; threshold scales by cohort size (0.10–0.35)."""
        if check_distinctiveness is None:
            return ValidationResult(
                passed=True,
                gate="G7",
                warnings=["check_distinctiveness not available (parallel sprint)"],
            )
        result = check_distinctiveness(personas)
        failures: list[str] = []
        if not result.passed:
            failures = [
                f"Mean pairwise cosine distance {result.mean_pairwise_distance:.3f} "
                f"is below threshold {result.threshold}. "
                f"Most similar pair: {result.most_similar_pair}"
            ]
        return ValidationResult(gate="G7", passed=result.passed, failures=failures)

    def g8_type_coverage(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G8: Type coverage per cohort size rules (N<3:1, 3<=N<5:2, 5<=N<10:3, N>=10:8)."""
        if check_type_coverage is None:
            return ValidationResult(
                passed=True,
                gate="G8",
                warnings=["check_type_coverage not available (parallel sprint)"],
            )
        passed, present, missing = check_type_coverage(personas)
        n = len(personas)
        # Determine required count using the same logic as _required_types
        _COVERAGE_RULES = {3: 2, 5: 3, 10: 8}
        if n < 3:
            required = 1
        elif n < 5:
            required = 2
        elif n < 10:
            required = 3
        else:
            required = 8
        failures: list[str] = []
        if not passed:
            missing_labels = [t.value if hasattr(t, "value") else str(t) for t in missing]
            failures = [
                f"Required {required} distinct types, found {len(present)}. "
                f"Missing: {missing_labels}"
            ]
        return ValidationResult(gate="G8", passed=passed, failures=failures)

    def g9_tension_completeness(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G9: Every persona has >= 1 explicit tension in derived_insights.key_tensions."""
        failures: list[str] = []
        for persona in personas:
            if len(persona.derived_insights.key_tensions) < 1:
                failures.append(
                    f"Persona {persona.persona_id}: no tensions in derived_insights.key_tensions"
                )
        return ValidationResult(gate="G9", passed=len(failures) == 0, failures=failures)

    def g11_tendency_source(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G11: Every tendency field has source != None."""
        failures: list[str] = []
        for persona in personas:
            for field_name in ["price_sensitivity", "switching_propensity", "trust_orientation"]:
                obj = getattr(persona.behavioural_tendencies, field_name, None)
                if obj is not None and hasattr(obj, "source") and obj.source is None:
                    failures.append(
                        f"Persona {persona.persona_id}: {field_name}.source is None"
                    )
        return ValidationResult(gate="G11", passed=len(failures) == 0, failures=failures)
