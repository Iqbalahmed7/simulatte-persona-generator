"use strict";
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "The Simulatte Persona Engine";
pres.author = "Simulatte";

// ── PALETTE ─────────────────────────────────────────────────────────────────
const P = {
  bg:    "0A1628",   // deep navy
  card:  "0F1E35",   // card bg
  card2: "142645",   // alternate card
  dark2: "1A3050",   // border / nested bg
  strip: "050D1A",   // footer strip
  teal:  "00D4C8",   // electric teal
  tdark: "006E6A",   // dark teal for callouts
  tmid:  "009994",   // mid teal for stacks
  white: "FFFFFF",
  lgray: "B8C8D8",   // body text
  gray:  "607080",   // muted text
  neg:   "E05C72",   // red for "NOT" items
  gold:  "FFD166",   // accent gold
};

// ── HELPERS ──────────────────────────────────────────────────────────────────

const mkShadow = () => ({ type: "outer", color: "000000", blur: 10, offset: 3, angle: 135, opacity: 0.20 });

function addFooter(s) {
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.31, w: 10, h: 0.315, fill: { color: P.strip }, line: { color: P.strip } });
  s.addText([
    { text: "Simulatte", options: { bold: true, color: P.teal } },
    { text: "  ·  Confidential  ·  2026", options: { color: P.gray } },
  ], { x: 0.35, y: 5.325, w: 9.3, h: 0.26, fontSize: 7.5, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
}

function addTopBar(s) {
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.055, fill: { color: P.teal }, line: { color: P.teal } });
}

function addTitle(s, text, y = 0.25) {
  s.addText(text, {
    x: 0.4, y, w: 9.2, h: 0.62,
    fontSize: 24, bold: true, color: P.teal,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0,
  });
}

function addCard(s, x, y, w, h, color, accentLeft = false) {
  const bg = color || P.card;
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: bg }, line: { color: P.dark2, width: 0.75 }, shadow: mkShadow() });
  if (accentLeft) {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.065, h, fill: { color: P.teal }, line: { color: P.teal } });
  }
}

function addCallout(s, text, x, y, w, h, bg, tc, fs = 11) {
  const bgc = bg || P.tdark;
  const textc = tc || P.white;
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: bgc }, line: { color: bgc } });
  s.addText(text, {
    x: x + 0.18, y, w: w - 0.36, h,
    fontSize: fs, color: textc, fontFace: "Calibri",
    italic: true, align: "center", valign: "middle", margin: 0,
  });
}

// ── SLIDE 1: TITLE ───────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };

  // Left vertical teal accent
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.07, h: 5.625, fill: { color: P.teal }, line: { color: P.teal } });
  // Top horizontal teal accent
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.07, fill: { color: P.teal }, line: { color: P.teal } });
  // Bottom accent
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.555, w: 10, h: 0.07, fill: { color: P.teal }, line: { color: P.teal } });

  // Main title
  s.addText("The Simulatte\nPersona Engine", {
    x: 0.55, y: 1.0, w: 9, h: 1.55,
    fontSize: 52, bold: true, color: P.white, fontFace: "Calibri",
    align: "left", valign: "top", margin: 0,
  });

  // Teal subtitle
  s.addText("A Native Method for Generating Behaviorally Coherent Synthetic Populations", {
    x: 0.55, y: 2.75, w: 8.8, h: 0.58,
    fontSize: 16, color: P.teal, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  // Tagline
  s.addText("Not a segment with a story.  A synthetic person with identity, memory, and cognitive agency.", {
    x: 0.55, y: 3.45, w: 8.5, h: 0.45,
    fontSize: 12.5, color: P.lgray, italic: true, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  // Footer
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.31, w: 10, h: 0.315, fill: { color: P.strip }, line: { color: P.strip } });
  s.addText([
    { text: "Simulatte", options: { bold: true, color: P.teal } },
    { text: "  ·  Confidential  ·  2026", options: { color: P.gray } },
  ], { x: 0.35, y: 5.325, w: 9.3, h: 0.26, fontSize: 7.5, fontFace: "Calibri", align: "right", valign: "middle", margin: 0 });
}

// ── SLIDE 2: THE PROBLEM ──────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Why Traditional Personas Fail");
  addFooter(s);

  const cols = [
    { x: 0.35, title: "Segment Models\nWearing Masks", body: "Demographics with a narrative bolted on. No agency. No memory. No internal contradiction. The persona looks like a person but can't behave like one." },
    { x: 3.52, title: "LLM-Generated\nDescriptions", body: "Plausible prose but no grounding. Repeatable stereotypes. Statistically averaged, not behaviorally specific. Every output regresses to the LLM's prior." },
    { x: 6.69, title: "Survey-Derived\nArchetypes", body: "Frozen in time. No temporal dimension. Can't be probed or simulated. Tells you what people said they'd do, not what they'd actually decide." },
  ];
  const CW = 3.0;
  cols.forEach(col => {
    addCard(s, col.x, 1.05, CW, 3.2, P.card, false);
    // Teal top accent
    s.addShape(pres.shapes.RECTANGLE, { x: col.x, y: 1.05, w: CW, h: 0.065, fill: { color: P.teal }, line: { color: P.teal } });
    // Icon number / visual element
    s.addShape(pres.shapes.OVAL, { x: col.x + CW / 2 - 0.22, y: 1.19, w: 0.44, h: 0.44, fill: { color: P.tdark }, line: { color: P.teal } });
    s.addText("✕", { x: col.x + CW / 2 - 0.22, y: 1.19, w: 0.44, h: 0.44, fontSize: 14, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(col.title, {
      x: col.x + 0.12, y: 1.72, w: CW - 0.24, h: 0.62,
      fontSize: 13, bold: true, color: P.white, fontFace: "Calibri",
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(col.body, {
      x: col.x + 0.14, y: 2.44, w: CW - 0.28, h: 1.72,
      fontSize: 10.5, color: P.lgray, fontFace: "Calibri",
      align: "left", valign: "top", margin: 0,
    });
  });

  addCallout(s, "The result: Personas that look real but behave like averages. Useless for decision simulation.", 0.35, 4.45, 9.3, 0.62, P.tdark, P.white, 12);
}

// ── SLIDE 3: THE RESEARCH ─────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Standing on Three Foundational Papers");
  addFooter(s);

  const pillars = [
    {
      x: 0.35, num: "01", tag: "DeepPersona (2024)",
      quote: "Personas need 8 anchor attributes that constrain all downstream filling — not demographics, but psychological decision-drivers.",
      insight: "Anchor-first construction. Modified the 8 to be decision-oriented: personality_type · risk_tolerance · trust_orientation · economic_constraint_level · life_stage_priority · primary_value_driver · social_orientation · tension_seed",
    },
    {
      x: 3.52, num: "02", tag: "Generative Agents (Park et al., 2023 · Stanford)",
      quote: "Synthetic agents with memory, reflection, and planning behave more consistently than stateless LLMs.",
      insight: "The perceive→remember→reflect→decide loop. Added the Core/Working memory split that Park et al. lacked — enabling experiment modularity and persona reuse.",
    },
    {
      x: 6.69, num: "03", tag: "MiroFish Framework",
      quote: "Behavioral archetypes derived from signal extraction outperform demographic-based segments for purchase prediction.",
      insight: "Grounding pipeline: extract signals from real text → cluster into behavioral archetypes → assign to personas. Anchors tendencies in evidence, doesn't substitute for simulation.",
    },
  ];

  const CW = 3.0;
  pillars.forEach(p => {
    addCard(s, p.x, 1.05, CW, 3.85, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x: p.x, y: 1.05, w: CW, h: 0.06, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(p.num, { x: p.x + 0.1, y: 1.14, w: 0.5, h: 0.38, fontSize: 20, bold: true, color: P.teal, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
    s.addText(p.tag, { x: p.x + 0.1, y: 1.54, w: CW - 0.2, h: 0.55, fontSize: 10.5, bold: true, color: P.white, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
    // Quote box
    s.addShape(pres.shapes.RECTANGLE, { x: p.x + 0.08, y: 2.17, w: CW - 0.16, h: 1.15, fill: { color: P.dark2 }, line: { color: P.dark2 } });
    s.addText('"' + p.quote + '"', { x: p.x + 0.16, y: 2.17, w: CW - 0.32, h: 1.15, fontSize: 9.5, color: P.lgray, italic: true, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
    s.addText("KEY INSIGHT ADOPTED", { x: p.x + 0.1, y: 3.42, w: CW - 0.2, h: 0.22, fontSize: 7.5, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(p.insight, { x: p.x + 0.1, y: 3.64, w: CW - 0.2, h: 1.15, fontSize: 9, color: P.lgray, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });

  addCallout(s, "Simulatte synthesizes all three into a unified engine. No single paper got it right.", 0.35, 5.0, 9.3, 0.22, P.bg, P.gray, 9.5);
}

// ── SLIDE 4: 5 PROPERTIES ─────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, 'What Makes a Persona "Real"? — The Five Properties');
  addFooter(s);

  const props = [
    { num: "1", label: "IDENTITY PERMANENCE", body: "Core identity is fixed. Life-defining events don't change. Values don't drift across experiments." },
    { num: "2", label: "MEMORY PERSISTENCE", body: "Experiences accumulate. Early stimuli influence later decisions. Context compounds over time." },
    { num: "3", label: "COGNITIVE AGENCY", body: "The LLM reasons through the persona's lens — perceives, reflects, and decides. It is not narrating." },
    { num: "4", label: "DOMAIN GROUNDING", body: "Behavioral tendencies anchored in empirical evidence when available. Behavioral data, not demographic proxies." },
    { num: "5", label: "EXPERIMENT MODULARITY", body: "Core memory immutable across experiments. Working memory resets per experiment for clean A/B testing." },
  ];

  const BW = 1.78;
  const gap = 0.10;
  const startX = 0.35;

  props.forEach((p, i) => {
    const x = startX + i * (BW + gap);
    addCard(s, x, 1.05, BW, 3.7, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.05, w: BW, h: 0.06, fill: { color: P.teal }, line: { color: P.teal } });
    // Number circle
    s.addShape(pres.shapes.OVAL, { x: x + BW / 2 - 0.26, y: 1.22, w: 0.52, h: 0.52, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(p.num, { x: x + BW / 2 - 0.26, y: 1.22, w: 0.52, h: 0.52, fontSize: 16, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(p.label, { x: x + 0.1, y: 1.87, w: BW - 0.2, h: 0.55, fontSize: 9.5, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(p.body, { x: x + 0.1, y: 2.50, w: BW - 0.2, h: 2.15, fontSize: 10, color: P.lgray, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });

  addCallout(s, "Remove any one of these five properties and you no longer have a persona. You have a template.", 0.35, 4.95, 9.3, 0.52, P.tdark, P.white, 12);
}

// ── SLIDE 5: BUSINESS FIT ────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Designed Around Business Problems, Not Research Demos");
  addFooter(s);

  // Left column header
  addCard(s, 0.35, 1.05, 4.35, 0.44, P.teal, false);
  s.addText("WHAT CLIENTS ACTUALLY NEED", { x: 0.45, y: 1.05, w: 4.15, h: 0.44, fontSize: 10, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });

  // Right column header
  addCard(s, 5.0, 1.05, 4.65, 0.44, P.dark2, false);
  s.addText("WHAT SIMULATTE DELIVERS", { x: 5.1, y: 1.05, w: 4.45, h: 0.44, fontSize: 10, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });

  const qItems = [
    '"Who is my buyer, really? Not demographics — behaviour."',
    '"How will a new product be received before launch?"',
    '"Which message lands with which segment?"',
    '"Can I test this campaign without a panel?"',
    '"Why did my last launch miss despite good research?"',
  ];
  const dItems = [
    "Deep persona profiles grounded in behavioral evidence — not survey averages",
    "Temporal simulation across 5–10 stimuli — purchase decision modeled, not stated",
    "Message testing across a synthetic population of 100–200 personas",
    "Full cohort generation from an ICP brief — no panels, no fieldwork",
    "Root-cause diagnosis: which persona rejected, which objection blocked, which driver was missing",
  ];

  const rowH = 0.56;
  qItems.forEach((q, i) => {
    const y = 1.58 + i * (rowH + 0.05);
    addCard(s, 0.35, y, 4.35, rowH, i % 2 === 0 ? P.card : P.card2, false);
    s.addText(q, { x: 0.50, y, w: 4.05, h: rowH, fontSize: 10.5, color: P.lgray, italic: true, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
  });

  dItems.forEach((d, i) => {
    const y = 1.58 + i * (rowH + 0.05);
    addCard(s, 5.0, y, 4.65, rowH, i % 2 === 0 ? P.card : P.card2, true);
    s.addText(d, { x: 5.15, y, w: 4.35, h: rowH, fontSize: 10.5, color: P.lgray, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
  });

  // Divider
  s.addShape(pres.shapes.RECTANGLE, { x: 4.78, y: 1.05, w: 0.14, h: 3.85, fill: { color: P.teal }, line: { color: P.teal } });
  s.addText("→", { x: 4.7, y: 2.8, w: 0.3, h: 0.4, fontSize: 18, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });

  addCallout(s, "Input: A business brief.  Output: A validated synthetic population ready to simulate.", 0.35, 4.98, 9.3, 0.55, P.tdark, P.white, 12);
}

// ── SLIDE 6: ARCHITECTURE OVERVIEW ───────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "The Six-Layer Architecture");
  addFooter(s);

  const layers = [
    { num: "01", label: "IDENTITY CONSTRUCTION", body: "Build the person — ~150 attributes, 8 anchors first, derived insights, life stories, narrative, core memory assembly.", color: "006E6A" },
    { num: "02", label: "DOMAIN TAXONOMY LAYER", body: "Plug in domain knowledge — domain-specific attributes extend the base taxonomy without touching the core engine (CPG, SaaS, Health, Child Nutrition…).", color: "007E79" },
    { num: "03", label: "GROUNDING PIPELINE  (Optional)", body: "Anchor in evidence — extract behavioral signals from real text → feature construction → K-means clustering → tendency assignment. Labels: grounded / proxy / estimated.", color: "008E88" },
    { num: "04", label: "COGNITIVE LOOP", body: "Run the simulation — Perceive → Remember → Reflect → Decide. Claude Haiku for perception (lightweight). Claude Sonnet for decisions and reflections (reasoning-heavy).", color: "009E98" },
    { num: "05", label: "CULTURAL REALISM LAYER  (Optional)", body: "Add cultural specificity — Sarvam enrichment for Indian markets. Enriches narrative expression, never decision logic.", color: "00B0AA" },
    { num: "06", label: "COHORT ASSEMBLY & VALIDATION", body: "Build the population — 100–200 personas validated for distinctiveness, distribution, and calibration. 11 structural gates + 6 behavioral validity tests.", color: "00C4BE" },
  ];

  const LH = 0.565;
  const GAP = 0.045;
  layers.forEach((l, i) => {
    const y = 1.05 + i * (LH + GAP);
    s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y, w: 9.3, h: LH, fill: { color: l.color }, line: { color: l.color } });
    s.addText(l.num, { x: 0.45, y, w: 0.55, h: LH, fontSize: 14, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: 1.08, y: y + 0.07, w: 0.02, h: LH - 0.14, fill: { color: P.bg }, line: { color: P.bg } });
    s.addText(l.label, { x: 1.18, y, w: 2.55, h: LH, fontSize: 10, bold: true, color: P.bg, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
    s.addText(l.body, { x: 3.85, y, w: 5.7, h: LH, fontSize: 9.5, color: P.bg, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
  });
}

// ── SLIDE 7: IDENTITY CONSTRUCTION ───────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Building the Person — 8 Steps, ~150 Attributes");
  addFooter(s);

  const steps = [
    { n: "1", label: "ANCHOR FILLING", body: "8 decision-drivers filled first: personality_type, risk_tolerance, trust_orientation, economic_constraint_level, life_stage_priority, primary_value_driver, social_orientation, tension_seed. These constrain everything downstream." },
    { n: "2", label: "PROGRESSIVE ATTRIBUTE FILLING", body: "Remaining ~142 attributes filled in batches. Soft correlations guide. Hard constraints (~50) block impossible combinations." },
    { n: "3", label: "DERIVED INSIGHTS", body: "7 fields computed deterministically: decision_style · trust_anchor · risk_appetite · primary_value_orientation · coping_mechanism · consistency_score (40–100) · key_tensions." },
    { n: "4", label: "LIFE STORY GENERATION", body: "2–3 life-defining events with lasting emotional impact. Contextualizes who the persona is and why they value what they value." },
    { n: "5", label: "TENDENCY ESTIMATION", body: "price_sensitivity (band + source) · trust_orientation (expert/peer/brand/ad weights) · switching_propensity · objection_profile (blocking objections)." },
    { n: "6", label: "NARRATIVE GENERATION", body: "2000-character first-person and third-person narratives. Reflects attributes, tensions, and life story. Written as a person, not a profile." },
    { n: "7", label: "CORE MEMORY ASSEMBLY", body: "Immutable identity: identity_statement · key_values (3–5) · life_defining_events · relationship_map · immutable_constraints · tendency_summary." },
    { n: "8", label: "VALIDATION GATES G1–G5", body: "Schema validity · hard constraints · tendency-attribute consistency · narrative completeness · narrative-attribute alignment." },
  ];

  const BH = 0.625;
  const GAP = 0.046;
  steps.forEach((st, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i % 4;
    const x = col === 0 ? 0.35 : 5.0;
    const y = 1.05 + row * (BH + GAP);
    const w = 4.5;

    addCard(s, x, y, w, BH, P.card, false);
    // Number badge
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.38, h: BH, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(st.n, { x, y, w: 0.38, h: BH, fontSize: 13, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(st.label, { x: x + 0.45, y: y + 0.03, w: w - 0.52, h: 0.24, fontSize: 8.5, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(st.body, { x: x + 0.45, y: y + 0.26, w: w - 0.52, h: BH - 0.3, fontSize: 8.5, color: P.lgray, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });
}

// ── SLIDE 8: THE TENSION SEED ─────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Every Persona Has a Contradiction Built In");
  addFooter(s);

  // Main statement
  addCard(s, 0.35, 1.0, 9.3, 0.72, P.dark2, false);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y: 1.0, w: 0.065, h: 0.72, fill: { color: P.teal }, line: { color: P.teal } });
  s.addText('"The most important design decision we made: every persona must contain at least one internal tension. Without tension, you get a stereotype."', {
    x: 0.55, y: 1.0, w: 9.0, h: 0.72,
    fontSize: 12.5, color: P.white, italic: true, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  const tensions = [
    { tag: "Price-aspirational  ×  Economically constrained", body: "Aspires to premium quality\n/ constrained by a ₹600 budget ceiling" },
    { tag: "Social  ×  Independent", body: "Trusts peer recommendations\n/ but resents feeling influenced" },
    { tag: "Analytical  ×  Intuitive", body: "Values research and evidence\n/ but makes final decisions on gut feel" },
    { tag: "Principled  ×  Pragmatic", body: "Health-conscious\n/ but won't override her child's taste preferences" },
  ];

  const TW = 4.5;
  const TH = 1.48;
  tensions.forEach((t, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = col === 0 ? 0.35 : 5.15;
    const y = 1.9 + row * (TH + 0.1);
    addCard(s, x, y, TW, TH, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: TW, h: 0.065, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(t.tag, { x: x + 0.12, y: y + 0.1, w: TW - 0.24, h: 0.28, fontSize: 8.5, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(t.body, { x: x + 0.12, y: y + 0.42, w: TW - 0.24, h: 0.96, fontSize: 12, color: P.white, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });

  s.addText("Tensions are the engine of non-stereotypical behavior. They produce motivated departures, objections, and edge cases that make simulation valuable.", {
    x: 0.35, y: 5.03, w: 9.3, h: 0.24,
    fontSize: 9.5, color: P.gray, italic: true, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0,
  });
}

// ── SLIDE 9: GROUNDING PIPELINE ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Anchoring Tendencies in Real Behavioral Evidence");
  addFooter(s);

  const stages = [
    {
      n: "01", label: "SIGNAL EXTRACTION",
      color: "006E6A",
      points: ["Raw text: reviews, forum posts, consumer language", "5 signal types: price_mention · purchase_trigger · rejection · switching · trust_citation", "Pure regex — no LLM calls", "Minimum 200 signals for grounding"],
    },
    {
      n: "02", label: "FEATURE CONSTRUCTION",
      color: "008582",
      points: ["Signals → 9-dimensional behavioral feature vectors", "Captures: price_salience_index · trust_source_distribution · objection_clusters", "One vector per signal document"],
    },
    {
      n: "03", label: "BEHAVIORAL CLUSTERING",
      color: "009E99",
      points: ["K-means on feature vectors", "Output: behavioral archetypes", "Not demographic segments — behavioral patterns", "Cluster count tuned per domain"],
    },
    {
      n: "04", label: "TENDENCY ASSIGNMENT",
      color: "00B8B2",
      points: ["Persona mapped to nearest archetype", "Behavioral tendencies updated with grounded parameters", "Source labeled: grounded · proxy · estimated"],
    },
  ];

  const SW = 2.1;
  const GAP = 0.14;
  stages.forEach((st, i) => {
    const x = 0.35 + i * (SW + GAP);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.05, w: SW, h: 3.75, fill: { color: st.color }, line: { color: st.color } });
    s.addText(st.n, { x, y: 1.1, w: SW, h: 0.4, fontSize: 18, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.12, y: 1.55, w: SW - 0.24, h: 0.03, fill: { color: P.bg }, line: { color: P.bg } });
    s.addText(st.label, { x: x + 0.1, y: 1.62, w: SW - 0.2, h: 0.5, fontSize: 9.5, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "top", margin: 0 });
    const bulletText = st.points.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < st.points.length - 1, color: P.bg, fontSize: 9, fontFace: "Calibri" } }));
    s.addText(bulletText, { x: x + 0.1, y: 2.2, w: SW - 0.2, h: 2.45, fontFace: "Calibri", fontSize: 9, color: P.bg, align: "left", valign: "top", margin: 0 });

    // Arrow between stages
    if (i < 3) {
      const ax = x + SW + 0.02;
      s.addText("▶", { x: ax, y: 2.5, w: 0.1, h: 0.35, fontSize: 11, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    }
  });

  addCallout(s, "Grounding is optional. The engine runs in Proxy Mode without domain data. But when data exists, it replaces guesswork with evidence.", 0.35, 5.0, 9.3, 0.52, P.tdark, P.white, 11.5);
}

// ── SLIDE 10: COGNITIVE LOOP ──────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "How a Persona Actually Thinks — The Cognitive Loop");
  addFooter(s);

  // Sub-headline
  s.addText("The LLM is not a narrator. It is a cognitive engine.", {
    x: 0.4, y: 0.9, w: 9.2, h: 0.3,
    fontSize: 13, bold: true, color: P.white, italic: true, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  const boxes = [
    {
      x: 0.35, y: 1.3, w: 4.45, h: 1.82,
      num: "1", step: "PERCEIVE", model: "Claude Haiku",
      points: ["Input: Stimulus + Core Memory", "Output: Observation (content, importance 1–10, emotional valence –1 to +1)", "What does this person notice and how do they feel about it?"],
    },
    {
      x: 5.2, y: 1.3, w: 4.45, h: 1.82,
      num: "2", step: "REMEMBER", model: "Automatic",
      points: ["Memory scoring: score = α·recency + β·importance + γ·relevance", "Top-20 memories retrieved per decision context", "Most relevant surface, not just most recent"],
    },
    {
      x: 0.35, y: 3.25, w: 4.45, h: 1.82,
      num: "3", step: "REFLECT", model: "Claude Sonnet  ·  triggers at importance accumulator > 80",
      points: ["Synthesizes patterns across observations", "Generates 1–3 reflections, each citing ≥2 source observations", "High-importance reflections (≥9, ≥3 citations) promoted to Core Memory"],
    },
    {
      x: 5.2, y: 3.25, w: 4.45, h: 1.82,
      num: "4", step: "DECIDE", model: "Claude Sonnet  ·  5-step reasoning chain",
      points: ["Step 1: Gut reaction  ·  Step 2: Information gathering  ·  Step 3: Constraint check  ·  Step 4: Social proof  ·  Step 5: Final decision", "Output: Decision + confidence (0–100) + reasoning trace + key drivers + objections"],
    },
  ];

  boxes.forEach(b => {
    addCard(s, b.x, b.y, b.w, b.h, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x: b.x, y: b.y, w: 0.38, h: b.h, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(b.num, { x: b.x, y: b.y, w: 0.38, h: b.h, fontSize: 16, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(b.step, { x: b.x + 0.46, y: b.y + 0.1, w: b.w - 0.54, h: 0.28, fontSize: 12, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(b.model, { x: b.x + 0.46, y: b.y + 0.38, w: b.w - 0.54, h: 0.24, fontSize: 8.5, color: P.gray, fontFace: "Calibri", align: "left", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: b.x + 0.46, y: b.y + 0.66, w: b.w - 0.54, h: 0.02, fill: { color: P.dark2 }, line: { color: P.dark2 } });
    const bulletText = b.points.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < b.points.length - 1, color: P.lgray, fontSize: 9.5, fontFace: "Calibri" } }));
    s.addText(bulletText, { x: b.x + 0.46, y: b.y + 0.74, w: b.w - 0.54, h: b.h - 0.82, fontFace: "Calibri", fontSize: 9.5, color: P.lgray, align: "left", valign: "top", margin: 0 });
  });

  // Loop arrows
  s.addText("→", { x: 4.82, y: 2.05, w: 0.36, h: 0.36, fontSize: 22, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  s.addText("↓", { x: 5.37, y: 3.1, w: 0.36, h: 0.28, fontSize: 22, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  s.addText("←", { x: 4.82, y: 4.0, w: 0.36, h: 0.36, fontSize: 22, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  s.addText("↑", { x: 0.0, y: 3.1, w: 0.36, h: 0.28, fontSize: 22, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
}

// ── SLIDE 11: MEMORY ARCHITECTURE ────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Memory is the Product");
  addFooter(s);

  // Core Memory column
  const coreItems = ["identity_statement", "key_values (3–5 priorities)", "life_defining_events", "relationship_map (decision partner, influencers, trust network)", "immutable_constraints (budget ceiling, non-negotiables, absolute avoidances)", "tendency_summary (natural language)"];
  const workItems = ["observations  (from perceive())", "reflections  (from reflect())", "plans", "brand_memories", "simulation_state"];

  // Core Memory card
  s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y: 1.05, w: 4.45, h: 0.5, fill: { color: P.teal }, line: { color: P.teal } });
  s.addText("CORE MEMORY", { x: 0.35, y: 1.05, w: 4.45, h: 0.5, fontSize: 15, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  s.addText("Immutable — Persists across ALL experiments", { x: 0.35, y: 1.57, w: 4.45, h: 0.28, fontSize: 9.5, color: P.teal, italic: true, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  addCard(s, 0.35, 1.9, 4.45, 3.05, P.card, false);
  const coreBullets = coreItems.map((c, j) => ({ text: c, options: { bullet: true, breakLine: j < coreItems.length - 1, color: P.lgray, fontSize: 11, fontFace: "Calibri" } }));
  s.addText(coreBullets, { x: 0.55, y: 1.95, w: 4.1, h: 2.9, fontFace: "Calibri", fontSize: 11, color: P.lgray, align: "left", valign: "top", margin: 0 });

  // Working Memory card
  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.05, w: 4.45, h: 0.5, fill: { color: P.dark2 }, line: { color: P.dark2 } });
  s.addText("WORKING MEMORY", { x: 5.2, y: 1.05, w: 4.45, h: 0.5, fontSize: 15, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  s.addText("Mutable — Resets between experiments", { x: 5.2, y: 1.57, w: 4.45, h: 0.28, fontSize: 9.5, color: P.gray, italic: true, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  addCard(s, 5.2, 1.9, 4.45, 3.05, P.card2, false);
  const workBullets = workItems.map((w, j) => ({ text: w, options: { bullet: true, breakLine: j < workItems.length - 1, color: P.lgray, fontSize: 11, fontFace: "Calibri" } }));
  s.addText(workBullets, { x: 5.4, y: 1.95, w: 4.1, h: 2.9, fontFace: "Calibri", fontSize: 11, color: P.lgray, align: "left", valign: "top", margin: 0 });

  // Divider symbol
  s.addText("⟷", { x: 4.82, y: 2.6, w: 0.36, h: 0.5, fontSize: 22, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });

  addCallout(s, "This split is the innovation Park et al. (2023) missed. Core permanence + working modularity = personas reusable across 100 experiments without contamination.", 0.35, 5.0, 9.3, 0.52, P.tdark, P.white, 11.5);
}

// ── SLIDE 12: NOT LLM ARTIFACTS ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "The Machinery That Prevents LLM Bleed-Through");
  addFooter(s);

  // Problem statement
  addCard(s, 0.35, 1.02, 9.3, 0.72, P.dark2, false);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y: 1.02, w: 0.07, h: 0.72, fill: { color: P.neg }, line: { color: P.neg } });
  s.addText('An LLM asked to "simulate a 34-year-old mother in Pune" generates average, plausible, statistically expected behavior. That\'s not a persona. That\'s the LLM\'s prior.', {
    x: 0.58, y: 1.02, w: 8.98, h: 0.72,
    fontSize: 12, color: P.white, italic: true, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  const mechanisms = [
    { n: "1", label: "ANCHOR CONSTRAINTS", body: "8 decision-driver anchors set before any LLM call. The LLM fills attributes within those constraints — not from its priors." },
    { n: "2", label: "HARD CONSTRAINT BLOCKING", body: '~50 impossible combinations encoded. The LLM cannot generate a "budget-constrained" persona with "premium brand affinity" unless a specific tension seed explains it.' },
    { n: "3", label: "TENSION SEEDS", body: "Every persona has a built-in contradiction that breaks statistical averages. The LLM must honor the tension — it cannot smooth it out." },
    { n: "4", label: "LIFE STORY GROUNDING", body: "The LLM generates decisions citing specific life events. It cannot drift to generic behavior because the life story constrains all reasoning." },
    { n: "5", label: "CITATION REQUIREMENTS", body: "Reflections must cite ≥2 source observations. Decisions validated against core memory. The LLM must show its work — and that work is persona-specific." },
  ];

  const MH = 0.6;
  const GAP = 0.055;
  mechanisms.forEach((m, i) => {
    const y = 1.87 + i * (MH + GAP);
    addCard(s, 0.35, y, 9.3, MH, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y, w: 0.38, h: MH, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(m.n, { x: 0.35, y, w: 0.38, h: MH, fontSize: 14, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(m.label, { x: 0.84, y: y + 0.06, w: 2.8, h: 0.26, fontSize: 9.5, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(m.body, { x: 0.84, y: y + 0.3, w: 8.65, h: 0.26, fontSize: 9.5, color: P.lgray, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });

  addCallout(s, "Two personas with similar demographics but different tensions, life stories, and anchors produce reliably different decisions. That's not fine-tuning. That's architecture.", 0.35, 5.0, 9.3, 0.52, P.tdark, P.white, 11.5);
}

// ── SLIDE 13: BELIEVABILITY STACK ────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Believability is Engineered, Not Prompted");
  addFooter(s);

  const layers = [
    { label: "TEMPORAL CONSISTENCY  (TOP)", body: "Same persona across 5 stimuli shows a consistent reasoning arc. Memory compounds. Confidence tracks the arc.", color: "00D4C8" },
    { label: "INTERNAL TENSION", body: "The contradiction that makes them human. The gap between aspiration and constraint. Between trust and independence.", color: "00B8B2" },
    { label: "BEHAVIORAL GROUNDING", body: "Tendencies anchored in real signal data when available. Price sensitivity from behavioral evidence, not demographic proxies.", color: "009E99" },
    { label: "NARRATIVE SPECIFICITY", body: "First-person voice, 2000 characters, citing specific life events. The persona has a past, not just a profile.", color: "008582" },
    { label: "PSYCHOLOGICAL COHERENCE", body: "~150 attributes filled with correlation checking. Soft correlations guide. Hard constraints block. No attribute is an island.", color: "006E6A" },
    { label: "DEMOGRAPHIC REALISM  (BASE)", body: "Age, location, household, life stage anchored to plausible profiles. Not random. Not averaged.", color: "005A56" },
  ];

  const LH = 0.555;
  const GAP = 0.048;
  const startY = 1.05;
  const LW = 7.5;

  layers.forEach((l, i) => {
    const y = startY + i * (LH + GAP);
    // Width increases from top to bottom (pyramid effect)
    const w = LW + (layers.length - 1 - i) * 0.05;
    const x = 0.35 + (9.3 - w) * 0 ;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y, w, h: LH, fill: { color: l.color }, line: { color: l.color } });
    s.addText(l.label, { x: 0.55, y, w: 2.95, h: LH, fontSize: 9.5, bold: true, color: P.bg, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: 3.55, y: y + 0.1, w: 0.02, h: LH - 0.2, fill: { color: P.bg }, line: { color: P.bg } });
    s.addText(l.body, { x: 3.65, y, w: w - 3.35, h: LH, fontSize: 9, color: P.bg, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
  });

  // Right-side callout
  addCard(s, 8.05, 1.05, 1.6, 3.9, P.card, false);
  s.addShape(pres.shapes.RECTANGLE, { x: 8.05, y: 1.05, w: 1.6, h: 0.065, fill: { color: P.teal }, line: { color: P.teal } });
  s.addText("Behavioral Validity Tests BV1–BV6 validate every layer.\n\nA persona that passes all six tests is not just plausible — it's behaviorally consistent across time.", {
    x: 8.12, y: 1.2, w: 1.44, h: 3.65,
    fontSize: 8.5, color: P.lgray, italic: true, fontFace: "Calibri",
    align: "left", valign: "top", margin: 0,
  });
}

// ── SLIDE 14: VALIDATION GATES ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Every Persona Earns Its Place — 11 Gates + 6 Behavioral Tests");
  addFooter(s);

  // G1-G11 table
  const tableRows = [
    [
      { text: "Gate", options: { fill: { color: P.teal }, color: P.bg, bold: true, fontFace: "Calibri", fontSize: 9.5 } },
      { text: "What It Checks", options: { fill: { color: P.teal }, color: P.bg, bold: true, fontFace: "Calibri", fontSize: 9.5 } },
      { text: "Threshold", options: { fill: { color: P.teal }, color: P.bg, bold: true, fontFace: "Calibri", fontSize: 9.5 } },
    ],
    ...[
      ["G1", "Schema validity (Pydantic)", "100%"],
      ["G2", "Hard constraints — impossible combinations", ">95%"],
      ["G3", "Tendency-attribute consistency", ">95%"],
      ["G4", "Narrative completeness", "100%"],
      ["G5", "Narrative-attribute alignment", ">90%"],
      ["G6", "Population distribution", ">90%"],
      ["G7", "Distinctiveness (cosine distance > 0.35)", ">85%"],
      ["G8", "Type coverage", ">90%"],
      ["G9", "Tension completeness", "100%"],
      ["G10", "Seed memory count (≥3 observations)", "100%"],
      ["G11", "Grounding label completeness", "100%"],
    ].map((row, i) => [
      { text: row[0], options: { fill: { color: i % 2 === 0 ? P.card : P.card2 }, color: P.teal, bold: true, fontFace: "Calibri", fontSize: 9 } },
      { text: row[1], options: { fill: { color: i % 2 === 0 ? P.card : P.card2 }, color: P.lgray, fontFace: "Calibri", fontSize: 9 } },
      { text: row[2], options: { fill: { color: i % 2 === 0 ? P.card : P.card2 }, color: P.white, bold: true, fontFace: "Calibri", fontSize: 9 } },
    ]),
  ];
  s.addTable(tableRows, { x: 0.35, y: 1.05, w: 5.6, colW: [0.55, 3.65, 1.1], border: { pt: 0.5, color: P.dark2 } });

  // BV1-BV6 right side
  s.addShape(pres.shapes.RECTANGLE, { x: 6.15, y: 1.05, w: 3.5, h: 0.44, fill: { color: P.dark2 }, line: { color: P.dark2 } });
  s.addText("BEHAVIORAL VALIDITY TESTS", { x: 6.15, y: 1.05, w: 3.5, h: 0.44, fontSize: 9.5, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });

  const bvTests = [
    { code: "BV1", text: "Repeated-run stability — same stimulus → same decision ±15 confidence" },
    { code: "BV2", text: "Memory-faithful recall — ≥80% high-importance recall, 100% citation validity" },
    { code: "BV3", text: "Temporal consistency — confidence trends match the stimulus arc" },
    { code: "BV4", text: "Interview realism — ≥3/5 responses cite life stories, 0 character breaks" },
    { code: "BV5", text: "Adjacent persona distinction — <50% shared language in reasoning" },
    { code: "BV6", text: "Override test — ≥1/2 overrides produce motivated departures" },
  ];
  bvTests.forEach((bv, i) => {
    const y = 1.59 + i * 0.6;
    addCard(s, 6.15, y, 3.5, 0.52, i % 2 === 0 ? P.card : P.card2, false);
    s.addShape(pres.shapes.RECTANGLE, { x: 6.15, y, w: 0.5, h: 0.52, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(bv.code, { x: 6.15, y, w: 0.5, h: 0.52, fontSize: 8, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(bv.text, { x: 6.72, y: y + 0.02, w: 2.86, h: 0.5, fontSize: 8.5, color: P.lgray, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
  });
}

// ── SLIDE 15: DISTINCTIVENESS ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "A Population, Not a Clone Army");
  addFooter(s);

  // Big stat
  s.addText("607%", {
    x: 0.35, y: 0.95, w: 9.3, h: 1.15,
    fontSize: 80, bold: true, color: P.teal, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0,
  });
  s.addText("better distinctiveness than baseline — measured on the LittleJoys pilot", {
    x: 0.35, y: 2.15, w: 9.3, h: 0.35,
    fontSize: 12, color: P.lgray, italic: true, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0,
  });
  // Sub note on how it's measured
  addCard(s, 2.5, 2.62, 5.0, 0.5, P.dark2, false);
  s.addText("Mean pairwise cosine distance on 8 anchor attributes across all 200 personas  ·  Threshold: > 0.35 required", {
    x: 2.62, y: 2.62, w: 4.76, h: 0.5,
    fontSize: 9, color: P.gray, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0,
  });

  const cols3 = [
    { x: 0.35, title: "What It Prevents", body: "Personas clustering around the same archetype. Cohorts that simulate the same decision. Research that merely confirms priors." },
    { x: 3.52, title: "How It's Enforced", body: "G7 gate rejects cohorts that fail the threshold. G6 ensures age/city/income spread. Dominant tensions are tracked and balanced across the cohort." },
    { x: 6.69, title: "Why It Matters", body: "A non-distinct cohort is a focus group where everyone agrees. The value of simulation is in the disagreement, the edge cases, the personas who reject." },
  ];
  cols3.forEach(c => {
    addCard(s, c.x, 3.27, 3.0, 1.78, P.card, true);
    s.addText(c.title, { x: c.x + 0.18, y: 3.35, w: 2.72, h: 0.32, fontSize: 10, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(c.body, { x: c.x + 0.18, y: 3.72, w: 2.72, h: 1.25, fontSize: 10, color: P.lgray, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });
}

// ── SLIDE 16: LITTLEJOYS PILOT ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Proof in Production — Indian Child Nutrition");
  addFooter(s);

  s.addText("LittleJoys / Nutrimix  ·  200 synthetic personas  ·  Indian market", {
    x: 0.4, y: 0.92, w: 9.2, h: 0.28,
    fontSize: 11, color: P.gray, italic: true, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  // Segment cards
  const segs = [
    { title: "New Mothers  (0–2 yrs)", n: "80", signals: "High: immunity_concern · pediatrician_influence · information_need" },
    { title: "Toddler Mothers  (2–5 yrs)", n: "70", signals: "High: child_taste_veto · brand_switch_tolerance · trial_pack_openness" },
    { title: "Elder Influencers  (45–65)", n: "50", signals: "High: ayurveda_affinity · food_first_belief · elder_advice_weight" },
  ];
  segs.forEach((seg, i) => {
    const x = 0.35 + i * 3.15;
    addCard(s, x, 1.28, 3.0, 1.5, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.28, w: 3.0, h: 0.06, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(seg.n + " personas", { x, y: 1.38, w: 3.0, h: 0.52, fontSize: 30, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(seg.title, { x: x + 0.1, y: 1.94, w: 2.8, h: 0.3, fontSize: 10, bold: true, color: P.white, fontFace: "Calibri", align: "center", margin: 0 });
    s.addText(seg.signals, { x: x + 0.1, y: 2.26, w: 2.8, h: 0.42, fontSize: 8.5, color: P.lgray, fontFace: "Calibri", align: "center", valign: "top", margin: 0 });
  });

  // Key results row
  const stats = [
    { val: "73.9%", label: "Buy + trial rate\nafter 5-stimulus sequence" },
    { val: "₹649", label: "Median WTP — matched\nactual ask price exactly" },
    { val: "42%", label: "Personas where primary\ndriver = pediatrician rec" },
    { val: "607%", label: "Distinctiveness above\nbaseline" },
    { val: "5", label: "Stimuli in the\nsimulation sequence" },
  ];
  const SW = 1.75;
  stats.forEach((st, i) => {
    const x = 0.35 + i * (SW + 0.1);
    addCard(s, x, 2.93, SW, 1.55, P.card2, false);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.93, w: SW, h: 0.055, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(st.val, { x, y: 3.02, w: SW, h: 0.72, fontSize: 28, bold: true, color: P.teal, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(st.label, { x: x + 0.06, y: 3.78, w: SW - 0.12, h: 0.62, fontSize: 8.5, color: P.lgray, fontFace: "Calibri", align: "center", valign: "top", margin: 0 });
  });

  addCallout(s, "The simulation diagnosed the mechanism — which stimulus moved which segment, which objection blocked, and exactly what it would take to convert the holdouts.", 0.35, 4.98, 9.3, 0.52, P.tdark, P.white, 11.5);
}

// ── SLIDE 17: USE CASES ──────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "The Engine is Domain-Agnostic. The Use Cases Are Not.");
  addFooter(s);

  const usecases = [
    { icon: "◆", label: "PRE-LAUNCH PRODUCT VALIDATION", body: "Simulate how 200 synthetic buyers respond to your product before a single rupee of fieldwork.", signal: "Purchase intent · objections · WTP distribution · which segment converts and why" },
    { icon: "◈", label: "MESSAGE & CREATIVE TESTING", body: "Run your copy, packaging, and campaign variants across your synthetic population.", signal: "Resonance by segment · message fatigue · framing effect · which claim lands" },
    { icon: "◇", label: "PRICING RESEARCH", body: "Find the real WTP distribution without anchoring bias from surveys.", signal: "Price sensitivity bands · objection-to-price correlation · elasticity by persona type" },
    { icon: "◉", label: "SEGMENTATION REDESIGN", body: "Replace demographic segments with behavioral archetypes derived from actual purchase signals.", signal: "Behavioral clusters · archetype definitions · decision-style distribution" },
    { icon: "▷", label: "SALES & GTM STRATEGY", body: "Map the objection landscape before your sales team hits the field.", signal: "Blocking objections by segment · trust source by archetype · conversion pathway" },
    { icon: "◎", label: "CONSUMER INSIGHT RESEARCH", body: "Build longitudinal synthetic panels that accumulate experience and can be probed over time.", signal: "Attitude shift across stimuli · belief change post-experience · qualitative depth" },
  ];

  const CW = 2.9;
  const CH = 1.58;
  const HGAP = 0.175;
  const VGAP = 0.1;
  usecases.forEach((uc, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.35 + col * (CW + HGAP);
    const y = 1.08 + row * (CH + VGAP);
    addCard(s, x, y, CW, CH, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: CW, h: 0.065, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(uc.icon + "  " + uc.label, { x: x + 0.12, y: y + 0.1, w: CW - 0.24, h: 0.32, fontSize: 8.5, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(uc.body, { x: x + 0.12, y: y + 0.44, w: CW - 0.24, h: 0.62, fontSize: 9.5, color: P.white, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.12, y: y + 1.1, w: CW - 0.24, h: 0.02, fill: { color: P.dark2 }, line: { color: P.dark2 } });
    s.addText("Signal: " + uc.signal, { x: x + 0.12, y: y + 1.14, w: CW - 0.24, h: 0.36, fontSize: 7.5, color: P.gray, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });

  s.addText("Current domain templates: Consumer Packaged Goods · B2B SaaS · Health & Wellness · Child Nutrition (India). Any domain extensible via taxonomy templates.", {
    x: 0.35, y: 5.02, w: 9.3, h: 0.24,
    fontSize: 9, color: P.gray, italic: true, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0,
  });
}

// ── SLIDE 18: SARVAM LAYER ───────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Cultural Specificity Without Cultural Drift — The Sarvam Layer");
  addFooter(s);

  s.addText("Enriching expression, never reasoning.", {
    x: 0.4, y: 0.92, w: 9.2, h: 0.3,
    fontSize: 14, bold: true, color: P.white, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  const sarvamCols = [
    {
      x: 0.35, title: "WHAT IT DOES", color: P.teal,
      points: [
        "Enriches persona narratives with regional, linguistic, and socioeconomic specificity for Indian markets",
        "Replaces generic defaults with culturally accurate details",
        "Scope: narrative_only · narrative_and_examples · full",
        "Opt-in only — never mandatory for clients",
      ],
    },
    {
      x: 3.52, title: "WHAT IT NEVER DOES", color: P.neg,
      points: [
        "Modifies decision logic or purchase decisions",
        "Triggers during perceive() / reflect() / decide() — post-core expression only",
        "Applies monolithic 'India' treatment — regional specificity is mandatory",
        "Runs without explicit client activation",
      ],
    },
    {
      x: 6.69, title: "THE CR1 GUARANTEE", color: P.gold,
      points: [
        "Validated by CR1 gate: enrichment must produce zero changes to any decision output",
        "The persona's reasoning is identical pre- and post-Sarvam",
        "Only the voice changes — not the logic",
        "CR2 & CR4: anti-stereotypicality and regional accuracy enforced",
      ],
    },
  ];

  const CW = 3.0;
  sarvamCols.forEach(c => {
    addCard(s, c.x, 1.3, CW, 3.45, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x: c.x, y: 1.3, w: CW, h: 0.06, fill: { color: c.color }, line: { color: c.color } });
    s.addText(c.title, { x: c.x + 0.12, y: 1.38, w: CW - 0.24, h: 0.38, fontSize: 10.5, bold: true, color: c.color, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
    const bullets = c.points.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < c.points.length - 1, color: P.lgray, fontSize: 10, fontFace: "Calibri" } }));
    s.addText(bullets, { x: c.x + 0.12, y: 1.85, w: CW - 0.24, h: 2.75, fontFace: "Calibri", fontSize: 10, color: P.lgray, align: "left", valign: "top", margin: 0 });
  });

  addCallout(s, "Anti-Stereotypicality Constraint: Every enriched persona must have cultural specificity that couldn't apply to any other Indian persona. Generic defaults fail the gate.", 0.35, 4.9, 9.3, 0.6, P.tdark, P.white, 11.5);
}

// ── SLIDE 19: WHAT SIMULATTE IS NOT ──────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "Deliberate Exclusions — What Simulatte Is Not");
  addFooter(s);

  const nots = [
    { label: "NOT a fine-tuned LLM", body: "No model training. No fine-tuning. The engine uses off-the-shelf Claude models. The realism comes from architecture — constraint systems, memory design, and cognitive loop — not from model weights." },
    { label: "NOT a survey tool", body: "Personas are not derived from survey responses. They are generated from behavioral signals + identity construction. They can simulate surveys, not reproduce them." },
    { label: "NOT a segment model", body: "Segments are statistical aggregates. Personas have individual identity, individual memory, individual history. The population emerges from 200 individuals, not one archetype split into types." },
    { label: "NOT a consulting deliverable", body: "Simulatte is a platform, not a one-time output. Personas persist. They can be recalled, re-simulated, updated with new stimuli. The asset compounds over time." },
  ];

  const BW = 4.45;
  const BH = 1.7;
  const GAP = 0.1;
  nots.forEach((n, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = col === 0 ? 0.35 : 5.2;
    const y = 1.1 + row * (BH + GAP);
    addCard(s, x, y, BW, BH, P.card, false);
    // Red accent top
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: BW, h: 0.065, fill: { color: P.neg }, line: { color: P.neg } });
    // X symbol
    s.addShape(pres.shapes.OVAL, { x: x + 0.12, y: y + 0.15, w: 0.42, h: 0.42, fill: { color: P.neg }, line: { color: P.neg } });
    s.addText("✕", { x: x + 0.12, y: y + 0.15, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: P.white, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(n.label, { x: x + 0.65, y: y + 0.15, w: BW - 0.75, h: 0.42, fontSize: 12, bold: true, color: P.neg, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
    s.addText(n.body, { x: x + 0.18, y: y + 0.7, w: BW - 0.34, h: 0.88, fontSize: 10.5, color: P.lgray, fontFace: "Calibri", align: "left", valign: "top", margin: 0 });
  });
}

// ── SLIDE 20: THE CONSTITUTION ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "What We Will Never Compromise — The Ten Principles");
  addFooter(s);

  const principles = [
    { n: "P1", label: "Persona ≠ segment model", body: "Identity, memory, history, cognition — all four required." },
    { n: "P2", label: "LLM is cognitive engine", body: "Not narrator. Perceive, reflect, decide — or it's not a simulation." },
    { n: "P3", label: "Memory is the product", body: "Temporal simulation is only possible because memory accumulates." },
    { n: "P4", label: "Tendencies are soft priors", body: "They shape reasoning. They do not replace it." },
    { n: "P5", label: "Identity > tendencies", body: "Same tendencies + different life stories = different people." },
    { n: "P6", label: "Grounding supports, doesn't replace", body: "Anchors tendencies. Does not compute decisions." },
    { n: "P7", label: "Calibration is a trust layer", body: "Comes after identity, memory, and cognition work." },
    { n: "P8", label: "Core is domain-agnostic", body: "Domain knowledge → taxonomy extensions. Never in the core." },
    { n: "P9", label: "Every persona has internal tension", body: "Contradiction prevents stereotypes. Always." },
    { n: "P10", label: "Transparency > performance", body: "Source labels, citations, documentation over black-box accuracy." },
  ];

  const RH = 0.485;
  const GAP = 0.04;
  const CW = 4.5;
  principles.forEach((p, i) => {
    const col = i < 5 ? 0 : 1;
    const row = i % 5;
    const x = col === 0 ? 0.35 : 5.15;
    const y = 1.05 + row * (RH + GAP);
    addCard(s, x, y, CW, RH, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.5, h: RH, fill: { color: P.teal }, line: { color: P.teal } });
    s.addText(p.n, { x, y, w: 0.5, h: RH, fontSize: 9, bold: true, color: P.bg, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(p.label, { x: x + 0.57, y: y + 0.04, w: CW - 0.65, h: 0.22, fontSize: 9.5, bold: true, color: P.teal, fontFace: "Calibri", align: "left", margin: 0 });
    s.addText(p.body, { x: x + 0.57, y: y + 0.25, w: CW - 0.65, h: 0.22, fontSize: 9, color: P.lgray, fontFace: "Calibri", align: "left", margin: 0 });
  });
}

// ── SLIDE 21: ROADMAP ────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };
  addTopBar(s);
  addTitle(s, "What's Coming");
  addFooter(s);

  // Timeline bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0.75, y: 2.02, w: 8.5, h: 0.06, fill: { color: P.dark2 }, line: { color: P.dark2 } });

  const phases = [
    {
      x: 0.35, dot_x: 1.0, label: "v1.0  ·  CURRENT", dotColor: P.teal,
      title: "Foundation",
      items: ["Individual persona generation + simulation", "Cohort assembly + validation", "4 domain templates", "Grounding pipeline (optional)", "Sarvam cultural layer", "REST API + CLI"],
    },
    {
      x: 3.52, dot_x: 4.17, label: "v1.1  ·  NEXT QUARTER", dotColor: P.tmid,
      title: "Calibration & Expansion",
      items: ["Behavioral parameter estimation from domain data", "Recency decay for irregular stimulus spacing", "Expanded templates: finance, edtech, D2C", "Improved reflection trigger calibration"],
    },
    {
      x: 6.69, dot_x: 7.34, label: "v2.0  ·  FUTURE", dotColor: P.gray,
      title: "Social Simulation",
      items: ["Multi-agent social simulation (personas influence each other)", "Longitudinal panel simulation (months of experience)", "Live data integration for real-time grounding", "White-label API for research platforms"],
    },
  ];

  const CW = 3.0;
  phases.forEach(p => {
    // Timeline dot
    s.addShape(pres.shapes.OVAL, { x: p.dot_x - 0.1, y: 1.97, w: 0.2, h: 0.2, fill: { color: p.dotColor }, line: { color: p.dotColor } });
    s.addText(p.label, { x: p.x, y: 1.6, w: CW, h: 0.3, fontSize: 8.5, bold: true, color: p.dotColor, fontFace: "Calibri", align: "center", margin: 0 });
    addCard(s, p.x, 2.25, CW, 2.82, P.card, false);
    s.addShape(pres.shapes.RECTANGLE, { x: p.x, y: 2.25, w: CW, h: 0.06, fill: { color: p.dotColor }, line: { color: p.dotColor } });
    s.addText(p.title, { x: p.x + 0.12, y: 2.33, w: CW - 0.24, h: 0.38, fontSize: 12, bold: true, color: P.white, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
    const bullets = p.items.map((item, j) => ({ text: item, options: { bullet: true, breakLine: j < p.items.length - 1, color: P.lgray, fontSize: 10, fontFace: "Calibri" } }));
    s.addText(bullets, { x: p.x + 0.12, y: 2.78, w: CW - 0.24, h: 2.2, fontFace: "Calibri", fontSize: 10, color: P.lgray, align: "left", valign: "top", margin: 0 });
  });
}

// ── SLIDE 22: CLOSING ────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: P.bg };

  // Left and top accents
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.07, fill: { color: P.teal }, line: { color: P.teal } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.07, h: 5.625, fill: { color: P.teal }, line: { color: P.teal } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.555, w: 10, h: 0.07, fill: { color: P.teal }, line: { color: P.teal } });

  s.addText("A Synthetic Population That\nThinks, Remembers, and Decides.", {
    x: 0.55, y: 0.85, w: 9.0, h: 1.6,
    fontSize: 40, bold: true, color: P.white, fontFace: "Calibri",
    align: "left", valign: "top", margin: 0,
  });

  s.addText("Built for the teams who can't afford to be wrong about their customer.", {
    x: 0.55, y: 2.62, w: 8.5, h: 0.45,
    fontSize: 14, color: P.teal, italic: true, fontFace: "Calibri",
    align: "left", valign: "middle", margin: 0,
  });

  const closings = ["Not a prompt.  A platform.", "Not a persona.  A population.", "Not a description.  A simulation."];
  closings.forEach((c, i) => {
    const y = 3.28 + i * 0.48;
    s.addText(c, {
      x: 0.55, y, w: 8.5, h: 0.42,
      fontSize: 16, bold: true, color: i === 0 ? P.teal : P.lgray, fontFace: "Calibri",
      align: "left", valign: "middle", margin: 0,
    });
  });

  // Footer
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.31, w: 10, h: 0.315, fill: { color: P.strip }, line: { color: P.strip } });
  s.addText([
    { text: "Simulatte", options: { bold: true, color: P.teal } },
    { text: "  ·  simulatte.ai  ·  Confidential  ·  2026", options: { color: P.gray } },
  ], { x: 0.35, y: 5.325, w: 9.3, h: 0.26, fontSize: 7.5, fontFace: "Calibri", align: "left", valign: "middle", margin: 0 });
}

// ── WRITE FILE ────────────────────────────────────────────────────────────────
const outPath = "/Users/admin/Documents/Simulatte Projects/Persona Generator/Simulatte_Persona_Engine.pptx";
pres.writeFile({ fileName: outPath })
  .then(() => console.log("✓ Saved:", outPath))
  .catch(err => { console.error("Error:", err); process.exit(1); });
