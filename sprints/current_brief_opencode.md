# SPRINT 20 BRIEF — OPENCODE
**Role:** ICP Spec Schema + Parser
**Sprint:** 20 — MiroFish Domain Taxonomy Extraction
**Spec ref:** Master Spec §6 (ICP Spec → Layer 3 anchor traits), §4 (Grounded Mode trigger)
**Previous rating:** 20/20

---

## Context

The ICP (Ideal Customer Profile) spec is the user-facing input document that triggers Grounded Mode. It defines: who the personas are for, what the business problem is, and optionally, "anchor traits" — specific attributes that must be present in the taxonomy.

You build two things:
1. The `ICPSpec` Pydantic model (the canonical representation of an ICP spec)
2. The parser that reads a user-provided ICP spec document (markdown or JSON) and returns an `ICPSpec` object

**Downstream dependency:** Cursor imports `ICPSpec` in `domain_extractor.py`. Your model must be available.

---

## File: `src/schema/icp_spec.py`

```python
"""src/schema/icp_spec.py

Pydantic model for the ICP (Ideal Customer Profile) specification.

The ICP spec is the user-facing input that defines who personas are built for.
It triggers Grounded Mode when domain data is also provided.

Spec ref: Master Spec §6 — "Layer 3: User-Specified Anchors (0-10 attributes).
From the ICP Spec 'Anchor Traits' section."
"""

from pydantic import BaseModel, Field

class ICPSpec(BaseModel):
    domain: str                          # e.g. "child_nutrition", "saas_b2b"
    business_problem: str                # e.g. "Understand why parents defer Nutrimix purchases"
    target_segment: str                  # e.g. "Urban Indian parents, children 2-12, Tier 1-2 cities"
    anchor_traits: list[str] = Field(default_factory=list)
    # Attribute names that MUST be in the domain taxonomy.
    # e.g. ["pediatrician_trust", "clean_label_preference"]

    data_sources: list[str] = Field(default_factory=list)
    # Description of domain data provided, e.g. ["2,010 signals from LJ research corpus"]

    geography: str | None = None         # Primary market geography
    category: str | None = None          # Product category, e.g. "CPG", "SaaS"
    persona_count: int = 10              # Target cohort size (default 10)

    class Config:
        extra = "ignore"                 # Accept extra fields from diverse ICP formats
```

---

## File: `src/taxonomy/icp_spec_parser.py`

```python
"""src/taxonomy/icp_spec_parser.py

Parse ICP spec documents into ICPSpec objects.

Supports two formats:
  1. JSON — flat dict with keys matching ICPSpec fields (or reasonable synonyms)
  2. Markdown — structured document with ## headers

Spec ref: Master Spec §6 — "ICP Spec + domain data trigger ontology extraction"
"""
```

### `parse_icp_spec(source: str | Path | dict) -> ICPSpec`

**Logic:**

```
If source is a dict → parse as JSON format (see below)
If source is a Path → read the file
  If file extension is .json → parse as JSON
  Else → parse as Markdown
If source is a str:
  Try json.loads() → if succeeds, parse as JSON
  Else → parse as Markdown
```

**JSON format parsing:**

Accept key synonyms:
- `domain` | `domain_name` | `category` (in absence of `domain`)
- `business_problem` | `problem` | `objective`
- `target_segment` | `segment` | `target_audience` | `icp`
- `anchor_traits` | `anchors` | `forced_attributes` | `required_traits`
- `data_sources` | `data` | `sources`

**Markdown format parsing:**

Recognize these header patterns (case-insensitive):
```
## Domain              → domain
## Business Problem    → business_problem
## Target Segment      → target_segment
## Anchor Traits       → anchor_traits (parse as bullet list: "- trait_name")
## Data Sources        → data_sources (parse as bullet list)
## Geography           → geography
## Category            → category
## Persona Count       → persona_count (parse as integer)
```

Extract the text block under each header (until next `##` header).
Strip leading/trailing whitespace. For anchor_traits and data_sources, parse bullet items (lines starting with `- ` or `* `).

**Fallback:** If a required field (`domain`, `business_problem`, `target_segment`) cannot be parsed from either format, raise `ValueError` with a descriptive message.

### Example markdown ICP spec the parser must handle:

```markdown
## Domain
child_nutrition

## Business Problem
Understand why urban Indian parents defer purchasing Littlejoys Nutrimix despite awareness

## Target Segment
Urban Indian parents with children aged 2-12, Tier 1-2 cities, household income ₹8-30 LPA

## Anchor Traits
- pediatrician_trust
- clean_label_preference
- child_acceptance_concern

## Data Sources
- 2,010 consumer signals from LittleJoys research corpus

## Geography
India (Tier 1-2 cities)

## Category
CPG
```

---

## Tests to support

Antigravity will test:
- JSON parsing with all key synonyms
- Markdown parsing with the example above
- Missing required field raises `ValueError`
- Extra unknown fields in JSON are silently ignored (Pydantic `extra = "ignore"`)
- Empty anchor_traits list when section absent

---

## Outcome file

Write `sprints/outcome_opencode.md`. Note any parsing edge cases you found, and confirm tests pass.
