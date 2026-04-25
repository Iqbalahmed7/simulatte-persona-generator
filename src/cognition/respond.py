"""src/cognition/respond.py — Generate a first-person conversational reply.

Used by The Mind demo (mind.simulatte.io) to wrap a DecisionOutput into
a natural, in-character response the persona would actually say out loud.

Separate from decide.py so the two concerns stay clean:
  decide.py  → structured 5-step reasoning (for the "show reasoning" panel)
  respond.py → natural first-person voice (for the chat bubble)

Uses Haiku for speed — called after decide() which uses Sonnet.
Prompt caching on the per-persona system block (persona context is stable).
"""
from __future__ import annotations

import anthropic

from src.cognition.decide import DecisionOutput
from src.schema.persona import PersonaRecord

_HAIKU_MODEL = "claude-haiku-4-5-20251001"


async def respond(
    user_message: str,
    decision: DecisionOutput,
    persona: PersonaRecord,
    llm_client: anthropic.AsyncAnthropic | None = None,
    model: str = _HAIKU_MODEL,
) -> str:
    """Generate a natural first-person conversational reply from the persona.

    Takes the structured DecisionOutput from decide() and the persona's
    narrative context to produce a reply in the persona's authentic voice.

    Args:
        user_message: The question or scenario the user posed.
        decision: The DecisionOutput from decide().
        persona: The PersonaRecord (for narrative/voice context).
        llm_client: AsyncAnthropic client; creates one if None.
        model: Model to use (default: Haiku for latency).

    Returns:
        A 2-4 sentence first-person reply in the persona's voice.
    """
    if llm_client is None:
        llm_client = anthropic.AsyncAnthropic()

    dem = persona.demographic_anchor
    name = dem.name
    first_name = name.split()[0]
    age = dem.age
    city = dem.location.city
    narrative = persona.narrative.first_person
    key_values = ", ".join(persona.memory.core.key_values[:3])
    tendency = persona.memory.core.tendency_summary

    # System prompt is stable per persona — eligible for prompt caching.
    system_prompt = (
        f"You are {name}, {age}, living in {city}.\n\n"
        f"{narrative}\n\n"
        f"Your core values: {key_values}\n"
        f"{tendency}\n\n"
        f"Respond ONLY as {first_name} — in first person, conversationally, "
        f"2-4 sentences. Do not explain your reasoning process. "
        f"Do not use bullet points or headers. "
        f"Speak naturally, as you would to someone asking about your life and choices."
    )

    # User turn: feed the decision trace as context, ask for natural reply.
    decision_context = (
        f'You were asked: "{user_message}"\n\n'
        f"After thinking it through, your conclusion is: {decision.decision}\n"
        f"Your gut reaction was: {decision.gut_reaction}\n"
    )
    if decision.what_would_change_mind:
        decision_context += f"What could change your mind: {decision.what_would_change_mind}\n"

    decision_context += (
        f"\nNow respond naturally to the original question in your own words — "
        f"as {first_name} would actually say it, not as a formal analysis."
    )

    response = await llm_client.messages.create(
        model=model,
        max_tokens=300,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": decision_context}],
    )

    return response.content[0].text.strip()
