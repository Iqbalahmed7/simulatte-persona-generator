# Multi-Agent Playbook

How to orchestrate the 5-engineer AI team effectively. Based on Sprints 28 and 29.

---

## The Team

| Engineer | Model | Strength | Watch Out For |
|---|---|---|---|
| **Cursor** | Auto (Sonnet) | Architecture, complex classes, interfaces | Nothing major — most reliable overall |
| **Codex** | GPT-5.3 | Clean Python, algorithms, ruff-passing output | None observed |
| **Goose** | Grok-4-1-fast | Decision logic, batch scripts, concurrency | HTML entity bug (see below) |
| **Antigravity** | Gemini 3 Flash | Test coverage, schema assertions | Touches files outside scope; run pytest before signalling |
| **OpenCode** | GPT-5.4 Nano | UI, scripts, exports, lightweight tooling | None observed in Sprint 29 |

---

## Sprint Structure

### The Parallel Wave (Day 1 AM)
Fire Cursor, Codex, and Goose simultaneously. They own independent files.

**Gate condition:** All three must signal done before OpenCode or Antigravity start.
- OpenCode needs Codex's work to exist before it can add exports
- Antigravity needs all implementations to exist before tests can be written

### The Dependent Wave (Day 1 PM)
Fire OpenCode and Antigravity simultaneously once the gate is cleared.

---

## Brief Writing Rules

**1. One engineer = one file. Document ownership in the brief.**
Put a "Files to Create / Modify" table at the top of every brief. Put a "Do NOT Touch" list beneath it. Both are equally important.

**2. Include a verified field names section in every brief.**
Every brief that touches schema fields must include a verified field names block. Read schema.py before writing. Don't write from memory.

**3. Include a self-verify step before signalling done.**
For Goose especially:
```bash
python3 -c "import ast; ast.parse(open('scripts/X.py').read()); print('syntax OK')"
```
But also: call a function — don't just import. Broken f-strings only surface at runtime.

**4. Tell engineers what not to touch as explicitly as what to build.**
"Do NOT Touch: src/agents/agent.py" is as important as "CREATE: src/agents/reflection.py"

**5. For Antigravity: specify minimum test counts.**
"≥ 10 tests", "≥ 8 assertions". Without a floor, Antigravity may write 3 tests and consider the job done.

---

## The Goose HTML Entity Bug

**What happens:**
Goose's output passes through a serialisation layer that encodes:
- `'` → `&#39;`
- `<` → `&lt;`
- `"` → `\"`

**Where it shows up:**
- String literals in content (stimulus content, prompts)
- f-string dictionary subscripts: `f"{d['key']}"` → `f"{d[&#39;key&#39;]}"`
- Format specifiers: `{var:<15}` → `{var:&lt;15}`

**Why the self-verify check can miss it:**
`python3 -c "import scripts.X"` doesn't execute function bodies. A broken f-string only errors when the function runs. The syntax check passes. The runtime check fails.

**Fix:**
Read the full file after Goose delivers. Replace all instances of:
- `&#39;` → `'`
- `&lt;` → `<`
- `\"` → `"` (inside string literals, not JSON escaping)

Then verify with a function call: `python3 -c "from scripts.X import print_summary; print_summary({'total_personas': 5, 'errors': 0, 'decision_distribution': {}, 'wtp_stats': {}, 'top_drivers': {}, 'top_objections': {}})"`

**Root cause:** Not fixable on our end — it's in Goose's output pipeline. Work around it every sprint.

---

## Post-Sprint Review Ritual

After every sprint, score each engineer on:

| Dimension | Weight | What it measures |
|---|---|---|
| Spec Adherence | 30% | Did they build what the brief asked? |
| Code Quality | 30% | Clean, readable, no artefacts, passes linting |
| Coordination | 20% | Respected file ownership, no conflicts, noted dependencies |
| Delivery Cleanliness | 20% | Self-verified, no manual cleanup required |

**Sprint 28 scores:**
- Cursor: 88 — good but had field path errors
- Codex: 85 — same field path errors, but cleaner code
- Goose: 62 — HTML entity bug blocked both Cursor and Codex
- Antigravity: 95 — found 4 real schema bugs, fixed them
- OpenCode: 78 — confused CREATE vs RUN on one task

**Sprint 29 scores:**
- Cursor: 99 — flawless, added defensive improvement
- Codex: 99 — clean, modern Python, no issues
- Goose: 82 — HTML entity bug again, self-verify didn't catch f-string case
- OpenCode: 98 — clean, null-safe, fixed a pre-existing bug
- Antigravity: 91 — good tests but added a breaking `pytest_plugins` line to conftest

---

## Common Conflicts to Prevent

| Conflict | Prevention |
|---|---|
| Two engineers write `__init__.py` | Assign to one (OpenCode), note in both briefs |
| Antigravity imports from pre-existing modules with missing deps | In brief: "Do NOT add pytest_plugins entries. Do NOT import from src/analysis/" |
| Goose script crashes at runtime despite passing import check | In brief: "Self-verify by calling a function, not just importing" |
| Codex touches a file Cursor owns | "Do NOT Touch" section in brief |

---

## Brief Template

```markdown
# Sprint N — Brief: [ENGINEER NAME]

**Role:** [role]
**Model:** [model]
**Assignment:** [one-line summary]
**Est. duration:** X hours
**START:** [dependency condition or "immediately"]

---

## Files to Create / Modify

| Action | File |
|---|---|
| CREATE | path/to/file.py |
| MODIFY | path/to/other.py — [what specifically to add/change] |

## Do NOT Touch
- [file 1]
- [file 2]

---

## Verified Field Names
[Copy exact field paths from schema.py — never from memory]

---

## [Task sections]

---

## Self-Verify Before Signalling Done
[Specific commands to run]

---

## Acceptance Criteria
- [ ] [checkboxes]
```
