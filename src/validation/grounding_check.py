"""src/validation/grounding_check.py — G12 Simulation Grounding Check.

Three-type contamination validator for Simulatte simulation outputs.

Detects:
  T1 — Injected Product Facts: numeric claims in the product frame with no
       verifiable source.
  T2 — Impossible Persona Attributes: persona prior exposure or attributes
       that contradict known market facts (e.g. forbidden retail touchpoints).
  T3 — Quote Leakage: specific numbers in verbatim persona quotes that were
       never established in the product frame.

Usage:
    from src.validation.grounding_check import (
        GroundingIssue, GroundingReport,
        run_grounding_check, load_market_facts,
    )

    market_facts = load_market_facts("lumio")
    report = run_grounding_check(
        product_frame=product_frame_text,
        market_facts=market_facts,
        persona_outputs=list_of_persona_dicts,
        source_documents=list_of_source_strings,
    )
    if not report.passed:
        print(report.summary())
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_MARKET_FACTS_DIR = Path(__file__).parent / "market_facts"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GroundingIssue:
    """A single contamination finding from the grounding check.

    Attributes
    ----------
    issue_type:
        "T1" (injected product fact), "T2" (impossible persona attribute),
        or "T3" (quote leakage).
    severity:
        "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    persona_id:
        The persona that surfaced the issue, or None for T1 issues that apply
        to the product frame rather than a specific persona.
    location:
        Human-readable description of where in the output the issue was found
        (e.g. "persona prior_exposure field", "verbatim quote #2").
    contaminated_text:
        The exact text snippet that triggered the flag.
    reason:
        Why this text is problematic.
    suggested_fix:
        Actionable remediation guidance.
    """

    issue_type: str                   # "T1" | "T2" | "T3"
    severity: str                     # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    persona_id: Optional[str]
    location: str
    contaminated_text: str
    reason: str
    suggested_fix: str


@dataclass
class GroundingReport:
    """Aggregated result of a full G12 grounding check run.

    Attributes
    ----------
    passed:
        True only when there are zero CRITICAL or HIGH severity issues.
    issues:
        All issues found, ordered by severity then issue_type.
    clean_count:
        Number of personas (plus the product frame) that passed with zero
        issues.
    """

    passed: bool
    issues: list[GroundingIssue]
    clean_count: int

    def summary(self) -> str:
        """Return a formatted multi-line summary of the grounding check.

        Example::

            === G12 Simulation Grounding Check ===

              Result : FAIL  (2 CRITICAL, 1 HIGH, 0 MEDIUM, 0 LOW)
              Issues : 3 total
              Clean  : 4 elements passed with no issues

              T2  CRITICAL  persona:P03  prior_exposure field
                  "I saw it at Croma last month"
                  Reason: Lumio is Amazon-only; Croma is a forbidden touchpoint.
                  Fix: Remove Croma reference; replace with Amazon or online-only
                       discovery path.

        Returns
        -------
        str
            Ready-to-print multi-line string (no trailing newline).
        """
        lines: list[str] = []
        lines.append("=== G12 Simulation Grounding Check ===")
        lines.append("")

        result_label = "PASS" if self.passed else "FAIL"

        # Count by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in self.issues:
            sev = issue.severity.upper()
            if sev in severity_counts:
                severity_counts[sev] += 1

        severity_str = "  ".join(
            f"{count} {sev}" for sev, count in severity_counts.items()
        )
        lines.append(f"  Result : {result_label}  ({severity_str})")
        lines.append(f"  Issues : {len(self.issues)} total")
        lines.append(f"  Clean  : {self.clean_count} elements passed with no issues")

        if self.issues:
            lines.append("")
            for issue in self.issues:
                pid_str = (
                    f"persona:{issue.persona_id}"
                    if issue.persona_id
                    else "product_frame"
                )
                header = (
                    f"  {issue.issue_type}  {issue.severity:<8}  "
                    f"{pid_str}  {issue.location}"
                )
                lines.append(header)
                lines.append(f'      "{issue.contaminated_text}"')
                lines.append(f"      Reason: {issue.reason}")
                lines.append(f"      Fix: {issue.suggested_fix}")
                lines.append("")

        return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Matches: ₹1,234 or ₹1234 or Rs 1,234
_RE_RUPEE_AMOUNT = re.compile(r"(?:₹|Rs\.?\s*)\s*[\d,]+(?:\.\d+)?")

# Matches: 12%, 12.5%
_RE_PERCENTAGE = re.compile(r"\b\d+(?:\.\d+)?\s*%")

# Matches: "4 seconds", "22 seconds", "2 minutes", "6 months"
_RE_DURATION = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)

# Matches product model specs: "Vision 7", "Arc 5", "iPhone 14", "Redmi Note 12"
# Requires the word before the number to start with an uppercase letter (proper noun /
# product name) to avoid false positives on common lowercase phrases.
_RE_SPEC_VERSION = re.compile(r"\b([A-Z][A-Za-z0-9]{1,15}(?:\s+[A-Z][A-Za-z0-9]{1,15}){0,2})\s+(\d+(?:\.\d+)?)\b")

# Matches any standalone integer or decimal number
_RE_ANY_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")

# Superlative / unsourced claim words
_RE_SUPERLATIVE = re.compile(
    r"\b(fastest|best|only|first|number\s*one|#1|top)\b", re.IGNORECASE
)

# Ratings like "4.4/5" or "4★" or "4.4 out of 5"
_RE_RATING = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:/\s*5|★|out\s+of\s+5)\b", re.IGNORECASE
)


def _extract_numbers(text: str) -> list[str]:
    """Return all distinct numeric tokens found in *text*."""
    tokens: list[str] = []
    for match in _RE_RUPEE_AMOUNT.finditer(text):
        tokens.append(match.group())
    for match in _RE_PERCENTAGE.finditer(text):
        tokens.append(match.group())
    for match in _RE_DURATION.finditer(text):
        tokens.append(match.group())
    for match in _RE_RATING.finditer(text):
        tokens.append(match.group())
    # Bare integers / decimals not already captured
    for match in _RE_ANY_NUMBER.finditer(text):
        raw = match.group()
        # Include only if the number stands alone (not already in a matched token)
        already = any(raw in tok for tok in tokens)
        if not already:
            tokens.append(raw)
    return tokens


def _number_in_text(number_token: str, text: str) -> bool:
    """Return True if *number_token* (stripped of non-digits) appears in *text*."""
    # Normalise: strip currency symbols, spaces, asterisks
    clean = re.sub(r"[₹Rs.\s★,]", "", number_token)
    if not clean:
        return False
    return bool(re.search(re.escape(clean), re.sub(r"[₹Rs.\s★,]", "", text)))


# ---------------------------------------------------------------------------
# T1 — Injected Product Facts
# ---------------------------------------------------------------------------


def _check_t1(
    product_frame: str,
    source_documents: list[str],
) -> list[GroundingIssue]:
    """Scan *product_frame* for unsourced numeric claims and superlatives."""
    issues: list[GroundingIssue] = []
    all_sources = "\n".join(source_documents) if source_documents else ""

    # --- numeric checks ---
    # Collect all numeric tokens in the product frame
    for match in _RE_RUPEE_AMOUNT.finditer(product_frame):
        token = match.group()
        if not _number_in_text(token, all_sources):
            issues.append(
                GroundingIssue(
                    issue_type="T1",
                    severity="HIGH",
                    persona_id=None,
                    location="product_frame (price/currency claim)",
                    contaminated_text=token,
                    reason=(
                        f"Rupee amount '{token}' appears in the product frame "
                        "but cannot be traced to any source document."
                    ),
                    suggested_fix=(
                        "Add an explicit citation or source reference for this "
                        "price claim, or remove it from the product frame."
                    ),
                )
            )

    for match in _RE_PERCENTAGE.finditer(product_frame):
        token = match.group()
        if not _number_in_text(token, all_sources):
            issues.append(
                GroundingIssue(
                    issue_type="T1",
                    severity="MEDIUM",
                    persona_id=None,
                    location="product_frame (percentage claim)",
                    contaminated_text=token,
                    reason=(
                        f"Percentage '{token}' appears in the product frame "
                        "but cannot be traced to any source document."
                    ),
                    suggested_fix=(
                        "Cite the source of this percentage claim or remove it."
                    ),
                )
            )

    for match in _RE_DURATION.finditer(product_frame):
        token = match.group()
        if not _number_in_text(token, all_sources):
            issues.append(
                GroundingIssue(
                    issue_type="T1",
                    severity="HIGH",
                    persona_id=None,
                    location="product_frame (duration/time claim)",
                    contaminated_text=token,
                    reason=(
                        f"Duration '{token}' appears in the product frame "
                        "but cannot be traced to any source document."
                    ),
                    suggested_fix=(
                        "Replace the specific duration with a relative claim "
                        "('2x faster') or add a source reference."
                    ),
                )
            )

    # --- superlative / unsourced claim checks ---
    for match in _RE_SUPERLATIVE.finditer(product_frame):
        token = match.group()
        # Get surrounding context (up to 80 chars)
        start = max(0, match.start() - 40)
        end = min(len(product_frame), match.end() + 40)
        context = product_frame[start:end].strip()

        # Check if the surrounding sentence has a source marker
        has_citation = bool(
            re.search(r"\(source|according to|per |cited|verified", context, re.IGNORECASE)
        )
        if not has_citation and not _number_in_text(token, all_sources):
            issues.append(
                GroundingIssue(
                    issue_type="T1",
                    severity="MEDIUM",
                    persona_id=None,
                    location="product_frame (superlative/absolute claim)",
                    contaminated_text=context,
                    reason=(
                        f"Superlative claim '{token}' found in product frame "
                        "with no citation marker or source document backing."
                    ),
                    suggested_fix=(
                        "Add a source reference or soften the claim to a "
                        "comparative (e.g. 'faster' not 'fastest')."
                    ),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# T2 — Impossible Persona Attributes
# ---------------------------------------------------------------------------

_PERSONA_SCAN_FIELDS = (
    "prior_exposure",
    "backstory",
    "narrative",
    "first_person_summary",
    "first_person",
    "third_person",
    "channel_usage",
    "discovery_path",
)


def _check_t2(
    persona_outputs: list[dict],
    market_facts: dict,
) -> list[GroundingIssue]:
    """Check each persona against market_facts for impossible touchpoints."""
    issues: list[GroundingIssue] = []

    distribution = market_facts.get("distribution", {})
    forbidden: list[str] = distribution.get("forbidden_touchpoints", [])
    distribution_model: str = distribution.get("model", "")
    offline_retail: bool = distribution.get("offline_retail", True)

    # Offline-channel keywords to flag when brand is online-only
    _OFFLINE_KEYWORDS = [
        "offline", "in-store", "retail store", "physical store",
        "showroom", "walk-in", "floor display",
    ]

    for persona in persona_outputs:
        persona_id: Optional[str] = (
            persona.get("persona_id")
            or persona.get("id")
            or persona.get("name")
        )

        # --- collect all text to scan for this persona ---
        scan_texts: list[tuple[str, str]] = []  # (location_label, text)

        for field_name in _PERSONA_SCAN_FIELDS:
            value = persona.get(field_name)
            if isinstance(value, str) and value.strip():
                scan_texts.append((f"{field_name} field", value))

        # Also scan all verbatim quotes
        quotes = _extract_quotes(persona)
        for idx, q in enumerate(quotes):
            scan_texts.append((f"verbatim quote #{idx + 1}", q))

        # --- forbidden touchpoint check ---
        for location_label, text in scan_texts:
            for touchpoint in forbidden:
                if touchpoint.lower() in text.lower():
                    issues.append(
                        GroundingIssue(
                            issue_type="T2",
                            severity="CRITICAL",
                            persona_id=persona_id,
                            location=location_label,
                            contaminated_text=_extract_snippet(text, touchpoint),
                            reason=(
                                f"Forbidden touchpoint '{touchpoint}' found. "
                                f"Brand distribution model is '{distribution_model}'. "
                                "This retail channel does not exist for this brand."
                            ),
                            suggested_fix=(
                                f"Remove reference to '{touchpoint}'. Replace with an "
                                "online discovery path (e.g. 'saw it on Amazon', "
                                "'found it through an online search')."
                            ),
                        )
                    )

        # --- offline channel_usage check (online-only brands) ---
        if not offline_retail and distribution_model:
            channel_usage = persona.get("channel_usage")
            if isinstance(channel_usage, (str, list)):
                channel_text = (
                    channel_usage
                    if isinstance(channel_usage, str)
                    else " ".join(str(c) for c in channel_usage)
                )
                for kw in _OFFLINE_KEYWORDS:
                    if kw.lower() in channel_text.lower():
                        issues.append(
                            GroundingIssue(
                                issue_type="T2",
                                severity="HIGH",
                                persona_id=persona_id,
                                location="channel_usage attribute",
                                contaminated_text=_extract_snippet(channel_text, kw),
                                reason=(
                                    f"Offline channel keyword '{kw}' in channel_usage "
                                    f"for a brand with distribution model '{distribution_model}'."
                                ),
                                suggested_fix=(
                                    "Remove offline channel references. Only online "
                                    "channels are valid for this brand."
                                ),
                            )
                        )

    return issues


# ---------------------------------------------------------------------------
# T3 — Quote Leakage
# ---------------------------------------------------------------------------


def _check_t3(
    product_frame: str,
    persona_outputs: list[dict],
) -> list[GroundingIssue]:
    """Check that numbers in verbatim quotes exist in the product frame."""
    issues: list[GroundingIssue] = []

    for persona in persona_outputs:
        persona_id: Optional[str] = (
            persona.get("persona_id")
            or persona.get("id")
            or persona.get("name")
        )

        quotes = _extract_quotes(persona)
        for idx, quote in enumerate(quotes):
            location = f"verbatim quote #{idx + 1}"

            # Extract numbers from the quote
            numbers = _extract_numbers(quote)
            for num_token in numbers:
                if not _number_in_text(num_token, product_frame):
                    issues.append(
                        GroundingIssue(
                            issue_type="T3",
                            severity="HIGH",
                            persona_id=persona_id,
                            location=location,
                            contaminated_text=quote[:200],
                            reason=(
                                f"Number '{num_token}' appears in a verbatim "
                                "persona quote but was never established in "
                                "the product frame fed to the simulation."
                            ),
                            suggested_fix=(
                                "Remove the specific number from the verbatim "
                                "quote, or add that number to the product frame "
                                "before running the simulation."
                            ),
                        )
                    )

            # Check technical specs (e.g. "Vision 7", "Arc 5")
            for spec_match in _RE_SPEC_VERSION.finditer(quote):
                spec_token = spec_match.group()
                if spec_token.lower() not in product_frame.lower():
                    # Avoid double-flagging if already caught by number check
                    already_flagged = any(
                        issue.contaminated_text[:50] == quote[:50]
                        and issue.reason.startswith(f"Number '{spec_match.group(2)}'")
                        for issue in issues
                        if issue.persona_id == persona_id and issue.location == location
                    )
                    if not already_flagged:
                        issues.append(
                            GroundingIssue(
                                issue_type="T3",
                                severity="HIGH",
                                persona_id=persona_id,
                                location=location,
                                contaminated_text=spec_token,
                                reason=(
                                    f"Technical spec '{spec_token}' in verbatim quote "
                                    "was not established in the product frame."
                                ),
                                suggested_fix=(
                                    "Ensure all model names and version numbers in "
                                    "verbatim quotes appear in the product frame."
                                ),
                            )
                        )

    return issues


# ---------------------------------------------------------------------------
# Quote extraction helper
# ---------------------------------------------------------------------------


def _extract_quotes(persona: dict) -> list[str]:
    """Return all verbatim quote strings from a persona dict."""
    quotes: list[str] = []

    # Common quote field patterns
    for key in ("quotes", "verbatim_quotes", "verbatim", "quote", "statements"):
        value = persona.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    quotes.append(item)
                elif isinstance(item, dict):
                    # {text: "...", context: "..."} or {quote: "..."}
                    for sub_key in ("text", "quote", "content", "verbatim"):
                        if isinstance(item.get(sub_key), str):
                            quotes.append(item[sub_key])
        elif isinstance(value, str):
            quotes.append(value)

    # Also check nested simulation_output / decision structures
    sim_output = persona.get("simulation_output") or persona.get("decision")
    if isinstance(sim_output, dict):
        for sub_key in ("verbatim", "quote", "gut_reaction", "reasoning_trace"):
            v = sim_output.get(sub_key)
            if isinstance(v, str):
                quotes.append(v)

    return [q for q in quotes if q.strip()]


def _extract_snippet(text: str, keyword: str, radius: int = 80) -> str:
    """Return a short snippet centred around *keyword* in *text*."""
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return text[:160]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(keyword) + radius)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_market_facts(client_name: str) -> dict:
    """Load market facts JSON for *client_name* from the market_facts directory.

    Args:
        client_name: Case-insensitive client identifier matching a JSON filename
                     in src/validation/market_facts/ (e.g. "lumio", "lo_foods",
                     "littlejoys").

    Returns:
        Parsed JSON dict.

    Raises:
        FileNotFoundError: If no matching JSON file exists.
        json.JSONDecodeError: If the JSON file is malformed.
    """
    filename = client_name.lower().replace(" ", "_").replace("-", "_") + ".json"
    path = _MARKET_FACTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"No market facts file found for client '{client_name}'. "
            f"Expected: {path}"
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def run_grounding_check(
    product_frame: str,
    market_facts: dict,
    persona_outputs: list[dict],
    source_documents: list[str] | None = None,
) -> GroundingReport:
    """Run T1, T2, and T3 contamination checks and return a GroundingReport.

    Args:
        product_frame:
            The stimulus/product brief text fed to the simulation. T1 and T3
            checks reference this text.
        market_facts:
            Dict loaded via load_market_facts() or constructed manually.
            Must contain a "distribution" key with "forbidden_touchpoints" list
            for T2 checks to function.
        persona_outputs:
            List of persona dicts.  Each dict may contain any subset of:
            prior_exposure, backstory, narrative, quotes, channel_usage, etc.
        source_documents:
            Optional list of source document strings (brand decks, press
            releases, spec sheets).  When provided, T1 checks use them to
            verify that product-frame claims are traceable.

    Returns:
        GroundingReport with passed=True only when zero CRITICAL/HIGH issues.
    """
    if source_documents is None:
        source_documents = []

    all_issues: list[GroundingIssue] = []

    # --- T1 ---
    t1_issues = _check_t1(product_frame, source_documents)
    all_issues.extend(t1_issues)

    # --- T2 ---
    t2_issues = _check_t2(persona_outputs, market_facts)
    all_issues.extend(t2_issues)

    # --- T3 ---
    t3_issues = _check_t3(product_frame, persona_outputs)
    all_issues.extend(t3_issues)

    # Sort: CRITICAL first, then HIGH, MEDIUM, LOW; then by issue_type
    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_issues.sort(
        key=lambda i: (_sev_order.get(i.severity, 9), i.issue_type, i.persona_id or "")
    )

    # passed = no CRITICAL or HIGH issues
    blocking = [i for i in all_issues if i.severity in ("CRITICAL", "HIGH")]
    passed = len(blocking) == 0

    # clean_count: personas with zero issues + the product frame if no T1 issues
    personas_with_issues = {
        i.persona_id for i in all_issues if i.persona_id is not None
    }
    clean_personas = len(persona_outputs) - len(personas_with_issues)
    product_frame_clean = 1 if not t1_issues else 0
    clean_count = clean_personas + product_frame_clean

    return GroundingReport(
        passed=passed,
        issues=all_issues,
        clean_count=clean_count,
    )
