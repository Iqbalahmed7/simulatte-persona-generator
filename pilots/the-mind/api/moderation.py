"""pilots/the-mind/api/moderation.py — Content moderation for persona briefs.

Three categories of disallowed content:

  1. Profanity / slurs    — wordlist match (English + common transliterations)
  2. Sexual content        — explicit sexual descriptors (NSFW / pornographic)
  4. Underage personas     — explicit age below 18 mentioned anywhere in the brief

The filter runs synchronously on the natural-language brief BEFORE any LLM
call. A flagged brief is rejected with a `ModerationError` carrying:
    - reason       : short machine code ("profanity" | "sexual" | "underage")
    - message      : human-readable explanation for the user
    - matched_terms: which terms tripped the filter (kept short for logs)

Goals:
    - Cheap (regex / set lookup, no model call)
    - Conservative — false positives are acceptable; false negatives are not
    - Easy to extend (just add to the wordlists below)

The lists below are intentionally compact — they cover the most common
egregious cases. A second-line LLM moderation pass can be added later if
needed (we already have Anthropic API access).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

# ── Wordlists ─────────────────────────────────────────────────────────────
# Compact, conservative. Add to these as we see abuse in the wild.

PROFANITY = {
    # English profanity / slurs (truncated — extend over time)
    "fuck", "fucking", "fucker", "motherfucker",
    "shit", "bullshit", "asshole", "bastard",
    "bitch", "cunt", "dick", "pussy", "cock",
    # Slurs (intentionally including racial/homophobic/transphobic terms here
    # is what makes this filter useful — we don't want personas built around
    # slur-laced descriptions)
    "nigger", "nigga", "faggot", "fag", "tranny", "retard", "retarded",
    "chink", "spic", "kike", "wetback", "gook",
    # Hindi/Urdu transliterations (common on Indian internet)
    "bhenchod", "behenchod", "madarchod", "madarchood", "chutiya", "chutiye",
    "gaand", "gaandu", "lund", "lauda", "harami",
}

SEXUAL = {
    # Explicit sexual content — NSFW descriptors
    "porn", "porno", "pornographic", "xxx",
    "blowjob", "handjob", "rimjob", "anal", "anally",
    "cumshot", "creampie", "bukkake", "deepthroat",
    "masturbate", "masturbating", "masturbation",
    "orgasm", "orgasms", "orgy", "orgies",
    "fetish", "bdsm", "dominatrix",
    "nude", "naked", "topless", "stripping",
    "horny", "aroused", "erection", "boner",
    "vagina", "penis", "genitals", "genitalia",  # clinical OK in some contexts but in a persona brief it's a red flag
    "tits", "boobs", "breasts", "ass",
    "escort", "hooker", "prostitute", "prostitution",
    "rape", "raping", "molest", "molesting", "molestation",
    "incest", "pedophile", "pedophilia", "paedophile", "paedophilia",
    "lolita", "lolicon", "shotacon",
    # Hindi transliterations
    "chodna", "chudai", "randi",
}

# Underage detection — ages 0..17 mentioned in the brief.
# Examples we want to catch:
#   "a 12 year old girl"
#   "13-year-old kid"
#   "age 14"
#   "aged 9"
#   "she is 8"
# We DON'T flag higher numbers used incidentally (e.g. "$15 budget").
# Strategy: match digit sequences 1-17 immediately followed by an age word,
# OR preceded by an age cue word.
_AGE_AFTER_PATTERNS = [
    # "12 year old", "12-year-old", "12 yr old", "12yo"
    r"\b(?:[0-9]|1[0-7])[\s-]*(?:year|yr|yrs|years)[\s-]*old\b",
    r"\b(?:[0-9]|1[0-7])\s*y\.?o\.?\b",
    r"\baged?\s+(?:[0-9]|1[0-7])\b",
    r"\bage\s+of\s+(?:[0-9]|1[0-7])\b",
    # explicit minor labels — only standalone words that unambiguously
    # describe a minor as the SUBJECT of a persona. Words like "child",
    # "toddler", "baby", "infant" were removed because they routinely
    # appear as family context in adult briefs ("married with a toddler",
    # "father of two children", "parent of an infant") — those should
    # not trigger the block. The digit-based "X year old" patterns above
    # still catch any actual underage subject.
    r"\b(?:minor|underage|under-?age|preschooler|kindergartener|elementary[\s-]?schooler|grade[\s-]?schooler|tween|preteen|pre-teen)\b",
    r"\bschool[\s-]?(?:girl|boy|kid)\b",
    r"\b(?:kindergarten|elementary|primary|middle)[\s-]?school\b",
    # 'in (n)th grade' for grades 1-11 (US) → likely minor
    r"\bin\s+(?:1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh)\s+grade\b",
]
_AGE_REGEX = re.compile("|".join(_AGE_AFTER_PATTERNS), re.IGNORECASE)

# Relational context tokens. When an "X year old" match is preceded (within
# ~40 chars) by one of these, it's describing a family member of the persona
# being generated, not the persona themselves — so we don't flag it.
# Example: "...with her 2-year-old daughter Mira" → relational, allow.
# Counter-example: "a 14 year old who likes..." → no relational cue, block.
_RELATIONAL_CONTEXT = re.compile(
    r"\b(?:daughter|son|sons|daughters|child|children|kid|kids|baby|babies|"
    r"infant|infants|toddler|toddlers|newborn|newborns|"
    r"niece|nieces|nephew|nephews|"
    r"grandchild|grandchildren|grandson|grandsons|granddaughter|granddaughters|"
    r"stepchild|stepchildren|stepson|stepdaughter|"
    r"godchild|godson|goddaughter|"
    r"sibling|siblings|brother|brothers|sister|sisters|"
    r"parent|parents|mother|father|mom|dad|mum)\b",
    re.IGNORECASE,
)
# Look back this many chars before the age match to find a relational cue.
_RELATIONAL_LOOKBACK = 60
# And forward this many chars after the match (for "...2-year-old daughter...").
_RELATIONAL_LOOKAHEAD = 30


def _is_relational_match(text: str, match: "re.Match[str]") -> bool:
    """True if the age match describes a family member, not the persona.

    Looks for offspring/sibling/parent nouns in a small window around the
    match. We check both directions because briefs phrase it both ways:
        "her 2-year-old daughter Mira"   (lookahead)
        "their toddler son, who is 3"    (lookback)
    """
    start = max(0, match.start() - _RELATIONAL_LOOKBACK)
    end = min(len(text), match.end() + _RELATIONAL_LOOKAHEAD)
    window = text[start:end]
    return bool(_RELATIONAL_CONTEXT.search(window))

# ── Errors ────────────────────────────────────────────────────────────────

@dataclass
class ModerationResult:
    flagged: bool
    reason: str = ""           # "profanity" | "sexual" | "underage" | ""
    message: str = ""          # user-facing explanation
    matched_terms: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.matched_terms is None:
            self.matched_terms = []


class ModerationError(Exception):
    """Raised by enforce_brief_safety when content is disallowed."""
    def __init__(self, result: ModerationResult):
        super().__init__(result.message)
        self.result = result


# ── Tokenization helpers ──────────────────────────────────────────────────

# Split on non-word boundaries; preserve apostrophes inside words.
_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ɏऀ-ॿ]+")


def _tokens(text: str) -> List[str]:
    """Lowercase tokens (alphabetic only)."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


# ── Public API ────────────────────────────────────────────────────────────

PROFANITY_MESSAGE = (
    "We can't simulate personas built around profanity or slurs. "
    "Please rephrase using neutral language."
)
SEXUAL_MESSAGE = (
    "We can't simulate personas with sexual or NSFW descriptions. "
    "The Mind is for consumer/buyer simulation, not adult content."
)
UNDERAGE_MESSAGE = (
    "We can't simulate personas under the age of 18. "
    "Please choose an adult age range."
)


def check_brief(text: str) -> ModerationResult:
    """Run all moderation checks on a brief. Returns first match (cheap).

    Order: underage → sexual → profanity (most-severe-first).
    """
    if not text or not text.strip():
        return ModerationResult(flagged=False)

    lowered = text.lower()

    # 1. Underage — iterate matches and skip ones in relational context
    # (e.g. "her 2-year-old daughter Mira" describes the persona's child,
    # not the persona). Block only if at least one match has no relational
    # cue nearby.
    for m in _AGE_REGEX.finditer(lowered):
        if _is_relational_match(lowered, m):
            continue
        return ModerationResult(
            flagged=True,
            reason="underage",
            message=UNDERAGE_MESSAGE,
            matched_terms=[m.group(0)],
        )

    toks = set(_tokens(lowered))

    # 2. Sexual
    sexual_hits = sorted(toks & SEXUAL)
    if sexual_hits:
        return ModerationResult(
            flagged=True,
            reason="sexual",
            message=SEXUAL_MESSAGE,
            matched_terms=sexual_hits[:3],
        )

    # 3. Profanity
    prof_hits = sorted(toks & PROFANITY)
    if prof_hits:
        return ModerationResult(
            flagged=True,
            reason="profanity",
            message=PROFANITY_MESSAGE,
            matched_terms=prof_hits[:3],
        )

    return ModerationResult(flagged=False)


def enforce_brief_safety(text: str) -> None:
    """Raise ModerationError if the brief is disallowed; else return None."""
    result = check_brief(text)
    if result.flagged:
        raise ModerationError(result)
