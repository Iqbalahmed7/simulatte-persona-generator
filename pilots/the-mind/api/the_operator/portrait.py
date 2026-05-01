"""the_operator/portrait.py — Twin portrait generation via fal.ai Flux.

Generates an AI portrait for a named real-world person using descriptive
signals (name, role, company, age/gender from synthesis profile) so Flux
produces the right demographic/phenotype — but NOT a likeness of the
actual individual. The result reads as "artificial yet plausibly real".

Always best-effort: returns None rather than raising, so portrait failure
never blocks the twin build.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("the_operator")

_NEGATIVE_PROMPT = (
    "cartoon, illustration, anime, 3d render, plastic skin, oversaturated, "
    "instagram filter, beauty filter, glamour shot, model agency portrait, "
    "perfect symmetry, stock photo pose, white background, id photo"
)

_FAL_ENDPOINT = "https://fal.run/fal-ai/flux-pro/v1.1-ultra"


def _build_twin_portrait_prompt(
    full_name: str,
    company: str | None,
    title: str | None,
    profile: dict,
) -> str:
    """Build a Flux prompt for a twin portrait.

    Uses the full name for heritage/phenotype signal — without it, Flux
    over-represents white phenotypes in cosmopolitan cities (same rationale
    as _build_portrait_prompt in main.py). The image is a plausible-looking
    person of that background, not a likeness of the actual individual.
    """
    age: str | int = profile.get("age") or profile.get("estimated_age") or ""
    gender = str(profile.get("gender", "")).lower()
    location = profile.get("location") or profile.get("city") or ""

    gender_word = (
        "woman" if gender == "female"
        else "man" if gender == "male"
        else "person"
    )
    age_clause = f"{age}-year-old " if age else ""
    location_clause = f" based in {location}" if location else ""

    role_parts = [p for p in [title, company] if p]
    role_clause = f", {', '.join(role_parts)}" if role_parts else ", senior executive"

    return (
        f"Candid photorealistic portrait of a {age_clause}{gender_word} "
        f"named {full_name}{location_clause}{role_clause}. "
        "Phenotype, skin tone, hair texture, and facial features consistent "
        "with the cultural and ethnic background implied by the name. "
        "Business-casual attire, well-tailored — confident yet approachable expression. "
        "Shot on Sony A7 III, 85mm f/1.8 lens, natural window light, shallow depth of field. "
        "Authentic skin texture, realistic pores, natural hair, genuine relaxed expression. "
        "Upper body framing, slightly off-axis gaze, neutral modern office environment. "
        "Hyper-realistic photograph, not a painting, not illustrated, "
        "no filters, no text, no watermark, looks like a real person photographed on a Tuesday."
    )


async def generate_twin_portrait(
    full_name: str,
    company: str | None,
    title: str | None,
    profile: dict,
) -> str | None:
    """Generate a twin portrait via fal.ai Flux. Returns URL or None on any failure.

    Best-effort — never raises. Portrait absence degrades gracefully to initials.
    """
    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        logger.warning("[operator] FAL_KEY not set — skipping twin portrait")
        return None

    prompt = _build_twin_portrait_prompt(full_name, company, title, profile)
    logger.debug("[operator] twin portrait prompt: %s", prompt[:120])

    try:
        async with httpx.AsyncClient(timeout=120) as http:
            resp = await http.post(
                _FAL_ENDPOINT,
                headers={
                    "Authorization": f"Key {fal_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": prompt,
                    "negative_prompt": _NEGATIVE_PROMPT,
                    "aspect_ratio": "3:4",
                    "num_images": 1,
                    "enable_safety_checker": True,
                    "output_format": "jpeg",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        images = data.get("images", [])
        if not images:
            logger.warning("[operator] fal.ai returned no images for %s", full_name)
            return None

        url: str = images[0]["url"]
        logger.info("[operator] twin portrait generated twin=%s url=%s", full_name, url[:60])
        return url

    except Exception as exc:  # noqa: BLE001
        logger.warning("[operator] portrait generation failed for %s: %s", full_name, exc)
        return None
