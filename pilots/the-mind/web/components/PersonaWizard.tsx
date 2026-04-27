"use client";

/**
 * PersonaWizard.tsx — chip-only persona builder.
 *
 * 4 chip steps + 1 optional 1-line text. Composes a coherent natural-language
 * brief from selections and submits to the same /generate-persona SSE endpoint
 * via the parent.
 *
 * Design: non-intrusive (max 1 line of typing), one decision per step,
 * back-navigable, brand-consistent (signal green for selection, parchment
 * neutral elsewhere).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { ICPForm } from "@/lib/api";

interface Chip {
  value: string;
  label: string;
  /** Phrase fragment used when composing the brief. */
  brief: string;
}

const DOMAIN_CHIPS: Chip[] = [
  { value: "cpg", label: "Consumer Goods", brief: "consumer-goods buyer" },
  { value: "saas", label: "SaaS / Tech", brief: "B2B SaaS buyer" },
  { value: "health_wellness", label: "Health & Wellness", brief: "health-and-wellness consumer" },
  { value: "finance", label: "Finance", brief: "personal-finance consumer" },
  { value: "education", label: "Education", brief: "learner / parent of school-age child" },
  { value: "other", label: "Something else", brief: "everyday consumer" },
];

const REGION_CHIPS: Chip[] = [
  { value: "in", label: "India", brief: "based in India" },
  { value: "us", label: "United States", brief: "based in the United States" },
  { value: "uk", label: "United Kingdom", brief: "based in the UK" },
  { value: "eu", label: "Europe", brief: "based in continental Europe" },
  { value: "sea", label: "South-East Asia", brief: "based in South-East Asia" },
  { value: "any", label: "Doesn't matter", brief: "" },
];

const AGE_CHIPS: Chip[] = [
  { value: "18-24", label: "18–24", brief: "in their early twenties" },
  { value: "25-34", label: "25–34", brief: "in their late twenties to early thirties" },
  { value: "35-44", label: "35–44", brief: "in their late thirties to early forties" },
  { value: "45-54", label: "45–54", brief: "in their late forties to early fifties" },
  { value: "55-64", label: "55–64", brief: "in their late fifties to early sixties" },
  { value: "65+", label: "65+", brief: "in their late sixties or older" },
];

const ARCHETYPE_CHIPS: Chip[] = [
  { value: "skeptic", label: "The Skeptic", brief: "naturally skeptical of brand claims, reads reviews carefully, slow to switch" },
  { value: "enthusiast", label: "The Enthusiast", brief: "early adopter, loves trying new products, posts about purchases" },
  { value: "pragmatist", label: "The Pragmatist", brief: "values-driven, price-sensitive, buys for utility not status" },
  { value: "loyalist", label: "The Loyalist", brief: "fiercely brand-loyal, sticks with what works, hard to convert" },
  { value: "minimalist", label: "The Minimalist", brief: "buys less but better, hates clutter, decision-fatigued" },
  { value: "status", label: "The Aspirer", brief: "image-conscious, willing to pay for premium brands and signalling" },
];

interface Props {
  onSubmit: (form: ICPForm) => void;
  onSwitchToFree: () => void;
  error: string;
}

export default function PersonaWizard({ onSubmit, onSwitchToFree, error }: Props) {
  const [step, setStep] = useState(0); // 0..4 (4 = review)
  const [domain, setDomain] = useState<string>("");
  const [region, setRegion] = useState<string>("");
  const [age, setAge] = useState<string>("");
  const [archetype, setArchetype] = useState<string>("");
  const [extra, setExtra] = useState<string>("");

  const totalSteps = 5; // 4 chip steps + review
  const progress = ((step + 1) / totalSteps) * 100;

  const composedBrief = useMemo(() => {
    const dChip = DOMAIN_CHIPS.find((c) => c.value === domain);
    const rChip = REGION_CHIPS.find((c) => c.value === region);
    const aChip = AGE_CHIPS.find((c) => c.value === age);
    const arChip = ARCHETYPE_CHIPS.find((c) => c.value === archetype);

    const parts: string[] = [];
    // "A consumer-goods buyer in their late thirties, based in India."
    const subject = aChip
      ? `A ${dChip?.brief ?? "person"} ${aChip.brief}`
      : `A ${dChip?.brief ?? "person"}`;
    parts.push(subject + (rChip?.brief ? `, ${rChip.brief}.` : "."));

    if (arChip) parts.push(`Personality: ${arChip.brief}.`);
    if (extra.trim()) parts.push(extra.trim().slice(0, 200));

    return parts.join(" ");
  }, [domain, region, age, archetype, extra]);

  // Editable brief draft — auto-syncs from `composedBrief` until the user
  // types in the textarea. Once dirty, chip changes stop overwriting it.
  // The "↺ Reset" control flips it back to chip-derived.
  const [briefDraft, setBriefDraft] = useState<string>("");
  const briefDirtyRef = useRef(false);
  useEffect(() => {
    if (!briefDirtyRef.current) setBriefDraft(composedBrief);
  }, [composedBrief]);

  function editDraft(v: string) {
    briefDirtyRef.current = true;
    setBriefDraft(v);
  }
  function resetDraft() {
    briefDirtyRef.current = false;
    setBriefDraft(composedBrief);
  }

  function next() {
    setStep((s) => Math.min(s + 1, totalSteps - 1));
  }

  function back() {
    setStep((s) => Math.max(s - 1, 0));
  }

  function handleSubmit() {
    const finalBrief = (briefDraft.trim() || composedBrief).slice(0, 2000);
    onSubmit({
      brief: finalBrief,
      domain: domain || "cpg",
    });
  }

  // Auto-advance helpers — selecting a chip on a single-select step nudges forward.
  function pick(setter: (v: string) => void, value: string) {
    setter(value);
    setTimeout(next, 180);
  }

  return (
    <div className="space-y-8">
      {/* Progress + step indicator */}
      <div>
        <div className="flex items-center mb-3">
          <p className="text-[11px] font-mono text-static uppercase tracking-widest">
            Step {step + 1} / {totalSteps}
          </p>
        </div>
        <div className="h-px bg-parchment/10 relative">
          <div
            className="absolute inset-y-0 left-0 bg-signal transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      {step === 0 && (
        <Step
          title="What category?"
          hint="Pick the kind of buyer you want to simulate."
          chips={DOMAIN_CHIPS}
          selected={domain}
          onSelect={(v) => pick(setDomain, v)}
        />
      )}
      {step === 1 && (
        <Step
          title="Where do they live?"
          hint="Region shapes language, brands, and assumptions."
          chips={REGION_CHIPS}
          selected={region}
          onSelect={(v) => pick(setRegion, v)}
        />
      )}
      {step === 2 && (
        <Step
          title="What age range?"
          hint="Life stage drives most decisions."
          chips={AGE_CHIPS}
          selected={age}
          onSelect={(v) => pick(setAge, v)}
        />
      )}
      {step === 3 && (
        <Step
          title="What kind of buyer?"
          hint="Pick the archetype closest to the person you have in mind."
          chips={ARCHETYPE_CHIPS}
          selected={archetype}
          onSelect={(v) => pick(setArchetype, v)}
        />
      )}
      {step === 4 && (
        <ReviewStep
          composedBrief={composedBrief}
          briefDraft={briefDraft}
          briefDirty={briefDirtyRef.current && briefDraft !== composedBrief}
          onEditDraft={editDraft}
          onResetDraft={resetDraft}
          extra={extra}
          setExtra={setExtra}
          error={error}
          onSubmit={handleSubmit}
        />
      )}

      {/* Nav */}
      <div className="flex items-center justify-between pt-2">
        {step > 0 ? (
          <button
            onClick={back}
            className="text-xs font-mono text-parchment/50 hover:text-parchment transition-colors"
          >
            ← Back
          </button>
        ) : <span />}

        {step < totalSteps - 1 && (
          <button
            onClick={next}
            disabled={
              (step === 0 && !domain) ||
              (step === 1 && !region) ||
              (step === 2 && !age) ||
              (step === 3 && !archetype)
            }
            className="text-xs font-mono text-signal hover:text-parchment disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Skip →
          </button>
        )}
      </div>
    </div>
  );
}

/* ─────────────────── Step renderer ─────────────────── */

function Step({
  title,
  hint,
  chips,
  selected,
  onSelect,
}: {
  title: string;
  hint: string;
  chips: Chip[];
  selected: string;
  onSelect: (v: string) => void;
}) {
  return (
    <div>
      <h2 className="font-condensed font-bold text-parchment text-2xl mb-2">
        {title}
      </h2>
      <p className="text-parchment/50 text-sm mb-6">{hint}</p>
      <div className="flex gap-2 flex-wrap">
        {chips.map((c) => (
          <button
            key={c.value}
            type="button"
            onClick={() => onSelect(c.value)}
            className={
              "px-4 py-2.5 text-sm font-medium border transition-all " +
              (selected === c.value
                ? "border-signal text-signal bg-signal/5"
                : "border-parchment/15 text-parchment/70 hover:border-parchment/40 hover:text-parchment")
            }
          >
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────── Review step ─────────────────── */

function ReviewStep({
  composedBrief,
  briefDraft,
  briefDirty,
  onEditDraft,
  onResetDraft,
  extra,
  setExtra,
  error,
  onSubmit,
}: {
  composedBrief: string;
  briefDraft: string;
  briefDirty: boolean;
  onEditDraft: (v: string) => void;
  onResetDraft: () => void;
  extra: string;
  setExtra: (v: string) => void;
  error: string;
  onSubmit: () => void;
}) {
  const MAX = 100;
  const BRIEF_MAX = 2000;
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-condensed font-bold text-parchment text-2xl mb-2">
          Anything else?
        </h2>
        <p className="text-parchment/50 text-sm mb-4">
          One line max — a habit, a fear, a contradiction. Optional.
        </p>
        <div className="relative">
          <input
            type="text"
            value={extra}
            onChange={(e) => setExtra(e.target.value.slice(0, MAX))}
            placeholder="e.g. distrusts influencers but follows three of them"
            maxLength={MAX}
            className="w-full bg-transparent border border-parchment/15 px-4 py-3 text-sm text-parchment
                       placeholder-parchment/25 focus:outline-none focus:border-parchment/40 transition-colors"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-static">
            {extra.length}/{MAX}
          </span>
        </div>
      </div>

      {/* Editable brief preview — auto-syncs from chips until edited */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] font-mono text-static uppercase tracking-widest">
            Brief — edit before submitting
          </p>
          {briefDirty && (
            <button
              type="button"
              onClick={onResetDraft}
              className="text-[10px] font-mono text-parchment/40 hover:text-signal transition-colors"
              title="Discard your edits and rebuild from the chip selections"
            >
              ↺ Reset to selections
            </button>
          )}
        </div>
        <textarea
          value={briefDraft}
          onChange={(e) => onEditDraft(e.target.value.slice(0, BRIEF_MAX))}
          rows={5}
          maxLength={BRIEF_MAX}
          placeholder={composedBrief || "Pick chips above and your brief will appear here…"}
          className="w-full bg-parchment/[0.02] border border-parchment/15 focus:border-parchment/40
                     px-4 py-3 text-sm text-parchment/85 leading-relaxed placeholder-parchment/25
                     focus:outline-none transition-colors resize-none"
        />
        <p className="text-[10px] font-mono text-static mt-1.5">
          {briefDirty
            ? "Your edits will be used as-is. Reset to rebuild from chips."
            : "Auto-built from your selections. Edit freely — the wizard will stop overwriting it."}
        </p>
      </div>

      {error && (
        <div className="border border-parchment/15 p-4">
          <p className="font-mono text-xs text-static">{error}</p>
        </div>
      )}

      <button
        onClick={onSubmit}
        className="w-full py-4 font-condensed font-bold text-void bg-signal text-lg tracking-wide hover:bg-parchment transition-colors"
      >
        Simulate this person →
      </button>
    </div>
  );
}
