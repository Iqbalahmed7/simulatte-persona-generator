"""src/taxonomy/icp_spec_parser.py

Parse ICP spec documents into ICPSpec objects.

Supports two formats:
  1. JSON — flat dict with keys matching ICPSpec fields (or reasonable synonyms)
  2. Markdown — structured document with ## headers

Spec ref: Master Spec §6 — "ICP Spec + domain data trigger ontology extraction"
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.schema.icp_spec import ICPSpec
from src.taxonomy.base_taxonomy import BASE_TAXONOMY
from src.taxonomy.collision_detector import CollisionReport, detect_collisions

# Base taxonomy names resolved once at import time (deterministic, no I/O).
_BASE_TAXONOMY_NAMES: list[str] = [a.name for a in BASE_TAXONOMY]


def _attach_collision_report(spec: ICPSpec) -> ICPSpec:
    """Run collision detection and attach the report to *spec* in-place.

    Template attributes are not yet known at parse time, so an empty list is
    passed — template collision detection is deferred to the point where a
    domain template is selected.
    """
    report: CollisionReport = detect_collisions(
        icp_anchor_traits=spec.anchor_traits,
        base_taxonomy_names=_BASE_TAXONOMY_NAMES,
        template_attributes=[],
    )
    spec.collision_report = report
    return spec


# ---------------------------------------------------------------------------
# Key synonym maps for JSON parsing
# ---------------------------------------------------------------------------

_DOMAIN_KEYS = ("domain", "domain_name")
_BUSINESS_PROBLEM_KEYS = ("business_problem", "problem", "objective")
_TARGET_SEGMENT_KEYS = ("target_segment", "segment", "target_audience", "icp")
_ANCHOR_TRAITS_KEYS = ("anchor_traits", "anchors", "forced_attributes", "required_traits")
_DATA_SOURCES_KEYS = ("data_sources", "data", "sources")


def _first(d: dict, keys: tuple[str, ...], default=None):
    """Return the value from dict d for the first matching key, else default."""
    for key in keys:
        if key in d:
            return d[key]
    return default


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_json(data: dict) -> ICPSpec:
    """Build an ICPSpec from a dict, accepting key synonyms."""
    # domain: fall back to category only if neither domain nor domain_name present
    domain = _first(data, _DOMAIN_KEYS)
    if domain is None:
        domain = data.get("category")

    business_problem = _first(data, _BUSINESS_PROBLEM_KEYS)
    target_segment = _first(data, _TARGET_SEGMENT_KEYS)

    if domain is None:
        raise ValueError(
            "ICP spec is missing a required 'domain' field. "
            "Accepted keys: domain, domain_name (or category as fallback)."
        )
    if business_problem is None:
        raise ValueError(
            "ICP spec is missing a required 'business_problem' field. "
            "Accepted keys: business_problem, problem, objective."
        )
    if target_segment is None:
        raise ValueError(
            "ICP spec is missing a required 'target_segment' field. "
            "Accepted keys: target_segment, segment, target_audience, icp."
        )

    kwargs: dict = {
        "domain": domain,
        "business_problem": business_problem,
        "target_segment": target_segment,
    }

    anchor_traits = _first(data, _ANCHOR_TRAITS_KEYS)
    if anchor_traits is not None:
        kwargs["anchor_traits"] = anchor_traits

    data_sources = _first(data, _DATA_SOURCES_KEYS)
    if data_sources is not None:
        kwargs["data_sources"] = data_sources

    for optional in ("geography", "category", "persona_count"):
        if optional in data:
            kwargs[optional] = data[optional]

    return ICPSpec(**kwargs)


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

# Map of lowercase header text → ICPSpec field name
_HEADER_MAP: dict[str, str] = {
    "domain": "domain",
    "business problem": "business_problem",
    "target segment": "target_segment",
    "anchor traits": "anchor_traits",
    "data sources": "data_sources",
    "geography": "geography",
    "category": "category",
    "persona count": "persona_count",
}

_BULLET_RE = re.compile(r"^[\-\*]\s+(.+)$")


def _parse_markdown(text: str) -> ICPSpec:
    """Parse a markdown ICP spec document into an ICPSpec."""
    # Split into sections at each ## heading
    sections: dict[str, str] = {}
    current_header: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        header_match = re.match(r"^##\s+(.+)$", line.strip())
        if header_match:
            # Save previous section
            if current_header is not None:
                sections[current_header] = "\n".join(current_lines).strip()
            current_header = header_match.group(1).strip().lower()
            current_lines = []
        else:
            if current_header is not None:
                current_lines.append(line)

    # Save last section
    if current_header is not None:
        sections[current_header] = "\n".join(current_lines).strip()

    kwargs: dict = {}

    for header_text, field_name in _HEADER_MAP.items():
        if header_text not in sections:
            continue
        raw = sections[header_text]
        if not raw:
            continue

        if field_name in ("anchor_traits", "data_sources"):
            items = []
            for line in raw.splitlines():
                m = _BULLET_RE.match(line.strip())
                if m:
                    items.append(m.group(1).strip())
            kwargs[field_name] = items
        elif field_name == "persona_count":
            try:
                kwargs[field_name] = int(raw.strip())
            except ValueError:
                pass  # ignore malformed persona_count; default will be used
        else:
            kwargs[field_name] = raw.strip()

    # Validate required fields
    for required in ("domain", "business_problem", "target_segment"):
        if not kwargs.get(required):
            raise ValueError(
                f"ICP spec markdown is missing a required '## {required.replace('_', ' ').title()}' "
                f"section (field: {required!r})."
            )

    return ICPSpec(**kwargs)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_icp_spec(source: str | Path | dict) -> ICPSpec:
    """Parse an ICP spec from a dict, file path, JSON string, or markdown string.

    Args:
        source: One of:
            - dict: parsed directly as JSON format
            - Path: file read from disk; .json extension → JSON, else Markdown
            - str: attempted as JSON first; falls back to Markdown

    Returns:
        ICPSpec instance

    Raises:
        ValueError: if a required field (domain, business_problem, target_segment)
                    cannot be resolved from the source.
        FileNotFoundError: if source is a Path that does not exist.
    """
    if isinstance(source, dict):
        return _attach_collision_report(_parse_json(source))

    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
        if source.suffix.lower() == ".json":
            return _attach_collision_report(_parse_json(json.loads(text)))
        return _attach_collision_report(_parse_markdown(text))

    # source is a str
    try:
        data = json.loads(source)
        return _attach_collision_report(_parse_json(data))
    except json.JSONDecodeError:
        return _attach_collision_report(_parse_markdown(source))
