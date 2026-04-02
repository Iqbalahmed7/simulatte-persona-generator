"""Sarvam enrichment engine.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
Uses Claude (Haiku model) to enrich persona narratives with Indian
cultural texture. The PersonaRecord is read-only — never modified.
"""
from __future__ import annotations

import json
from typing import Any

from src.sarvam.config import SarvamConfig
from src.sarvam.types import (
    SarvamEnrichmentRecord,
    EnrichedNarrative,
    ContextualReplacement,
    ValidationStatus,
)


class SarvamEnricher:
    """Enriches persona narratives with Indian cultural texture.

    Uses Claude via the Anthropic client. The PersonaRecord is treated
    as a read-only input — the enricher never modifies it.
    """

    def __init__(self, llm_client: Any) -> None:
        """
        Args:
            llm_client: An Anthropic client instance (same as used in perceive/reflect/decide).
        """
        self.llm = llm_client

    async def enrich(
        self,
        persona: Any,           # PersonaRecord — typed as Any to avoid circular import
        config: SarvamConfig,
    ) -> SarvamEnrichmentRecord:
        """Run Sarvam enrichment on a finalized PersonaRecord.

        Activation pre-check is assumed to have already passed (caller verified).
        This method always attempts enrichment.

        Args:
            persona: A validated PersonaRecord (India + opt-in confirmed by caller).
            config: SarvamConfig with enrichment settings.

        Returns:
            SarvamEnrichmentRecord with enriched narratives and cultural references.
        """
        prompt = self._build_enrichment_prompt(
            persona=persona,
            scope=config.scope,
            strict=config.anti_stereotypicality_strict,
        )

        response_text = await self._call_llm(prompt, config.model)
        parsed = self._parse_enrichment_response(response_text)

        if not parsed or "enriched_first_person" not in parsed:
            # Fallback: return record with original narratives unchanged
            enriched_narrative = EnrichedNarrative(
                first_person=persona.narrative.first_person,
                third_person=persona.narrative.third_person,
            )
            return SarvamEnrichmentRecord(
                enrichment_applied=True,
                enrichment_provider="sarvam",
                enrichment_scope=config.scope,
                persona_id=persona.persona_id,
                enriched_narrative=enriched_narrative,
                cultural_references_added=[],
                contextual_examples_replaced=[],
                validation_status=ValidationStatus(),
            )

        enriched_narrative = EnrichedNarrative(
            first_person=parsed.get("enriched_first_person", persona.narrative.first_person),
            third_person=parsed.get("enriched_third_person", persona.narrative.third_person),
        )

        cultural_refs = parsed.get("cultural_references_added", [])
        if not isinstance(cultural_refs, list):
            cultural_refs = []

        replacements = []
        for r in parsed.get("contextual_examples_replaced", []):
            if isinstance(r, dict) and "original" in r and "replacement" in r:
                replacements.append(ContextualReplacement(
                    original=r.get("original", ""),
                    replacement=r.get("replacement", ""),
                    attribute_source=r.get("attribute_source", "unspecified"),
                ))

        return SarvamEnrichmentRecord(
            enrichment_applied=True,
            enrichment_provider="sarvam",
            enrichment_scope=config.scope,
            persona_id=persona.persona_id,
            enriched_narrative=enriched_narrative,
            cultural_references_added=cultural_refs,
            contextual_examples_replaced=replacements,
            validation_status=ValidationStatus(),
        )

    def _build_enrichment_prompt(
        self,
        persona: Any,
        scope: str,
        strict: bool,
    ) -> str:
        """Build the enrichment prompt from persona fields.

        The prompt instructs the LLM to:
        1. Read the persona profile (location, household, income, life stories, narrative)
        2. Rewrite first_person and third_person narratives with India-specific texture
        3. Replace generic/Western examples with India-specific equivalents
        4. Document every cultural reference added and what attribute it derives from
        5. NEVER change facts, values, tendencies, or decision-relevant content

        Anti-stereotypicality instructions (if strict=True):
        Explicitly list prohibited defaults (from spec §15 S-1 to S-5):
        - Do not assume joint family (check household.structure)
        - Do not assume Hindi-speaking (check location.region)
        - Do not assume low income (check income_bracket)
        - Do not use festival/arranged-marriage defaults unless traceable to life_stories
        - Match regional context: location.region + urban_tier

        Prompt must request structured JSON output in this format:
        {
            "enriched_first_person": "...",
            "enriched_third_person": "...",
            "cultural_references_added": ["ref1", "ref2"],
            "contextual_examples_replaced": [
                {"original": "...", "replacement": "...", "attribute_source": "..."}
            ]
        }
        """
        da = persona.demographic_anchor
        narrative = persona.narrative

        # Build profile block
        profile = (
            f"Name: {da.name}, Age: {da.age}, Gender: {da.gender}\n"
            f"Location: {da.location.city}, {da.location.region} ({da.location.urban_tier})\n"
            f"Country: {da.location.country}\n"
            f"Household: {da.household.structure}, size {da.household.size}, "
            f"income: {da.household.income_bracket}\n"
            f"Education: {da.education}, Employment: {da.employment}\n"
            f"Life stage: {da.life_stage}\n"
        )

        # Life stories
        stories_text = ""
        for story in persona.life_stories:
            stories_text += f"- {story.when}: {story.event} (impact: {story.lasting_impact})\n"

        # Tendency summary
        tendency_summary = persona.memory.core.tendency_summary if persona.memory else ""

        anti_stereo = ""
        if strict:
            anti_stereo = """
ANTI-STEREOTYPICALITY RULES (MUST FOLLOW):
- Do NOT assume joint family unless household.structure is "joint"
- Do NOT assume Hindi-speaking unless location.region is a Hindi belt
- Do NOT use wedding/festival/arranged marriage references unless traceable to a life story
- Do NOT assume low income unless income_bracket is explicitly low
- Match regional context: use references specific to the persona's city and region
- India is not one culture — be specific to this persona's geography and demographics
- Do NOT add jugaad, frugality, or thrift references unless lifestyle attributes support them
"""

        prompt = f"""You are enriching the narrative of an Indian persona with culturally authentic detail.

IMPORTANT RULES:
1. You are reading this persona as READ-ONLY. Do NOT change who they are.
2. Do NOT modify their values, tendencies, income level, household, or education.
3. Do NOT add new personality traits or change existing ones.
4. Only add cultural texture: specific Indian brands, institutions, channels, idioms.
5. Every cultural reference you add must trace to a specific persona field.
6. Match the word count of the original narrative (±20 words maximum).
{anti_stereo}
PERSONA PROFILE:
{profile}

LIFE STORIES:
{stories_text}

BEHAVIOURAL SUMMARY:
{tendency_summary}

CURRENT FIRST-PERSON NARRATIVE (100-150 words):
{narrative.first_person}

CURRENT THIRD-PERSON NARRATIVE (150-200 words):
{narrative.third_person}

TASK:
Enrich both narratives with India-specific cultural texture. Replace generic references
(e.g. "a supermarket") with India-specific ones (e.g. "D-Mart") where the persona's
location and income support it. Add authentic contextual detail.

Return ONLY valid JSON in this exact format:
{{
    "enriched_first_person": "...",
    "enriched_third_person": "...",
    "cultural_references_added": ["reference1", "reference2"],
    "contextual_examples_replaced": [
        {{"original": "...", "replacement": "...", "attribute_source": "location.city"}}
    ]
}}"""
        return prompt

    async def _call_llm(self, prompt: str, model: str) -> str:
        """Make a single LLM call and return the response text."""
        # If llm is already a BaseLLMClient (new path), use .complete()
        if hasattr(self.llm, 'complete'):
            return await self.llm.complete(
                system="You are a cultural enrichment expert for Indian personas.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                model=model,
            )
        # Legacy path: raw Anthropic client
        response = await self.llm.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _parse_enrichment_response(self, response_text: str) -> dict:
        """Parse the JSON enrichment response. Returns {} on parse failure."""
        # Extract JSON from response (handle markdown code blocks)
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return {}
