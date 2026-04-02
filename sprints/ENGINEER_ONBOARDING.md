# ENGINEER ONBOARDING — SIMULATTE PERSONA GENERATOR
**For all engineers. Read this before reading your sprint brief.**
**Owner: Tech Lead**

---

## What You Are Building

Simulatte is a synthetic persona platform. It generates deep, psychologically grounded synthetic personas that can be used in business experiments — surveys, simulations, decision modelling.

A persona is not a demographic profile. It is a fully specified psychological identity:
- ~150+ attribute values (continuous and categorical)
- Memory (core identity + working state)
- A cognitive loop (perceive, reflect, decide)
- Life stories and narrative
- Behavioural tendencies as soft priors, not numerical parameters

The output is a `PersonaRecord` — a Pydantic model that is the canonical representation of one synthetic person.

---

## The Files You Must Read First

Before touching your sprint brief, read these — in this order:

### 1. Master Spec (canonical source of truth)
```
SIMULATTE_PERSONA_GENERATOR_MASTER_SPEC.md
```
The authoritative specification. Every design decision traces back to this document.
Key sections for Sprint 1:
- **§5** — Persona Record Structure (the exact schema)
- **§6** — Taxonomy Strategy (base attributes, anchor-first filling)
- **§10** — Constraint System (hard/soft constraints, correlation rules)
- **§14** — Settled decisions, open questions, build order

### 2. Constitution
```
SIMULATTE_CONSTITUTION.md
```
10 principles and 10 anti-patterns. Read the anti-patterns especially — they document how similar systems have failed. The pre-implementation checklist at the end must be mentally verified before writing code.

**Most important principles for Sprint 1:**
- **P4** — Behavioural tendencies are natural-language priors, NOT numerical coefficients. Do not add floats where bands belong.
- **P8** — Domain-agnostic core. Base taxonomy has no product-specific attributes.
- **P10** — Every tendency must carry a `source` field.

### 3. Validity Protocol
```
SIMULATTE_VALIDITY_PROTOCOL.md
```
The test gates. Module 1 (G1–G11) is Sprint 1's acceptance criteria. Understand what you need to pass before you write the code.

### 4. Your Sprint Brief
```
sprints/current_brief_[your_name].md
```
Your specific deliverables, interface specs, constraints, and outcome file format.

---

## Repository Structure

```
SIMULATTE_PERSONA_GENERATOR_MASTER_SPEC.md   ← Read first
SIMULATTE_CONSTITUTION.md                    ← Read second
SIMULATTE_VALIDITY_PROTOCOL.md               ← Read third
SIMULATTE_SARVAM_TEST_PROTOCOL.md            ← India-specific layer (not Sprint 1)

references/
  architecture.md                            ← Prior architecture notes (partially superseded)
  competitive_landscape_deep_research.md     ← Market research
  output_schema.md                           ← Old schema (DO NOT follow — superseded by master spec)
  behavioural_grounding.md                   ← Old coefficient approach (DO NOT follow — superseded)

sprints/
  SPRINT_PLAN_V1.md                          ← Sprint map, all 7 sprints
  ENGINEER_ONBOARDING.md                     ← This file
  current_brief_cursor.md                    ← Cursor's brief
  current_brief_codex.md                     ← Codex's brief
  current_brief_goose.md                     ← Goose's brief
  current_brief_opencode.md                  ← OpenCode's brief
  current_brief_antigravity.md               ← Antigravity's brief

src/                                         ← Where you write your code
  schema/
    persona.py                               ← Cursor's deliverable
    cohort.py                                ← Cursor's deliverable
    validators.py                            ← Antigravity's deliverable
  taxonomy/
    base_taxonomy.py                         ← Codex's deliverable
    domain_templates/
      cpg.py                                 ← OpenCode's deliverable
      saas.py                                ← OpenCode's deliverable
      template_loader.py                     ← OpenCode's deliverable
  generation/
    attribute_filler.py                      ← Goose's deliverable
    stratification.py                        ← Antigravity's deliverable
    constraint_checker.py                    ← Antigravity's deliverable

pilots/
  lo-foods/                                  ← Existing pilot code (reference only)
```

---

## The Import Dependency Order

Build in this order — if you import from a file that doesn't exist yet, write your code against the interface, not the implementation:

```
1. src/schema/persona.py          (Cursor — no upstream deps)
2. src/schema/cohort.py           (Cursor — imports persona.py)
3. src/taxonomy/base_taxonomy.py  (Codex — no upstream deps)
4. src/taxonomy/domain_templates/ (OpenCode — imports base_taxonomy.py)
5. src/generation/constraint_checker.py  (Antigravity — imports schema + taxonomy)
6. src/generation/attribute_filler.py    (Goose — imports schema + taxonomy)
7. src/generation/stratification.py      (Antigravity — imports schema + taxonomy)
8. src/schema/validators.py              (Antigravity — imports all of the above)
```

For Sprint 1, all five engineers write simultaneously. If you need to import from a file that Cursor or Codex hasn't written yet, use type stubs or comment the import and proceed. The integration test happens after all five files are delivered.

---

## What NOT to Do

These are the most common failure modes. Avoid them:

1. **Do not add numerical coefficients to BehaviouralTendencies.** No `purchase_probability: float`, no `price_elasticity: float`. Tendencies are bands + descriptions.
2. **Do not add domain-specific attributes to base_taxonomy.py.** `saas_feature_complexity` does not belong in the base taxonomy. Domain templates are for that.
3. **Do not generate `derived_insights`, `behavioural_tendencies`, `narrative`, or `life_stories` in the attribute filler.** Those are Sprint 2.
4. **Do not skip the `source` field on Attribute or TendencyBand.** Every value must be traceable.
5. **Do not invent schema fields not in the master spec.** The spec says exactly what fields exist.

---

## How to Signal Completion

When your code is done:
1. Write your outcome file at `sprints/outcome_[your_name].md` (format is in your brief).
2. Your outcome file is what the Tech Lead reviews. Be specific about what you built, what was hard, and what edge cases you found.

---

## One-Line Summary Per Engineer

| Engineer | Your job in one line |
|----------|---------------------|
| **Cursor** | Build the Pydantic v2 schema — every other file imports from yours |
| **Codex** | Build the base attribute taxonomy — ~150 attributes across 6 categories |
| **Goose** | Build the attribute filler — progressive conditional LLM filling of all attributes |
| **OpenCode** | Build the domain extension templates (CPG + SaaS) and the template loader |
| **Antigravity** | Build the validators, constraint checker, and stratification engine |
