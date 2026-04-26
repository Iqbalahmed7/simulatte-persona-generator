"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { generatePersona, ICPForm, GenerationEvent } from "@/lib/api";

const COUNTRIES = [
  "India", "United States", "United Kingdom", "Germany",
  "Brazil", "Singapore", "UAE", "Australia",
];

const DOMAINS = [
  { value: "cpg", label: "Consumer Goods / FMCG" },
  { value: "saas", label: "SaaS / Technology" },
  { value: "health", label: "Health & Wellness" },
  { value: "general", label: "General" },
];

const GENDERS = [
  { value: "any", label: "Any" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
];

const INCOME_LEVELS = [
  { value: "lower_middle", label: "Lower middle class" },
  { value: "middle", label: "Middle class" },
  { value: "upper_middle", label: "Upper middle class" },
  { value: "affluent", label: "Affluent" },
];

const EMPTY_FORM: ICPForm = {
  brand_name: "",
  product_category: "",
  business_problem: "",
  country: "India",
  age_range: "25-40",
  gender: "any",
  income_level: "middle",
  domain: "cpg",
};

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-sans font-semibold tracking-widest uppercase text-static mb-2">
        {label}
      </label>
      {hint && <p className="text-xs text-parchment/40 mb-2">{hint}</p>}
      {children}
    </div>
  );
}

const inputCls =
  "w-full bg-transparent border border-parchment/15 px-4 py-3 text-sm text-parchment " +
  "placeholder-parchment/25 focus:outline-none focus:border-parchment/40 transition-colors";

const selectCls =
  "w-full bg-void border border-parchment/15 px-4 py-3 text-sm text-parchment " +
  "focus:outline-none focus:border-parchment/40 transition-colors appearance-none cursor-pointer";

export default function GeneratePage() {
  const router = useRouter();
  const [form, setForm] = useState<ICPForm>(EMPTY_FORM);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [error, setError] = useState("");

  const set = (k: keyof ICPForm, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.business_problem.trim()) return;
    setRunning(true);
    setSteps([]);
    setError("");

    try {
      await generatePersona(form, (event: GenerationEvent) => {
        if (event.type === "status" && event.message) {
          setSteps((prev) => [...prev, event.message!]);
        }
        if (event.type === "result" && event.persona_id) {
          router.push(`/persona/${event.persona_id}`);
        }
        if (event.type === "error" && event.message) {
          setError(event.message);
          setRunning(false);
        }
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setRunning(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-12 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Back
        </Link>
        <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mt-6 mb-3">
          Simulatte / Generate
        </p>
        <h1
          className="font-condensed font-bold text-parchment leading-none mb-3"
          style={{ fontSize: "clamp(36px,5vw,60px)" }}
        >
          Build a <span className="text-signal">persona.</span>
        </h1>
        <p className="text-parchment/60 text-base">
          Describe your ICP and we&apos;ll synthesise a behaviourally coherent person — complete with
          backstory, 120+ attributes, and decision psychology.
        </p>
      </div>

      {!running ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Row 1 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <Field label="Brand / Client name" hint="Optional">
              <input
                className={inputCls}
                placeholder="e.g. Himalaya, Notion, Zepto"
                value={form.brand_name}
                onChange={(e) => set("brand_name", e.target.value)}
              />
            </Field>
            <Field label="Product / Service category">
              <input
                className={inputCls}
                placeholder="e.g. herbal supplements, B2B SaaS"
                value={form.product_category}
                onChange={(e) => set("product_category", e.target.value)}
              />
            </Field>
          </div>

          {/* Business problem */}
          <Field
            label="Research question / business problem"
            hint="The core question this persona should help answer"
          >
            <textarea
              className={inputCls + " resize-none"}
              rows={3}
              placeholder="e.g. Will urban mothers aged 28-38 pay a premium for an immunity supplement with clinical backing?"
              value={form.business_problem}
              onChange={(e) => set("business_problem", e.target.value)}
              required
            />
          </Field>

          {/* Row 2 — market */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Field label="Country">
              <select className={selectCls} value={form.country} onChange={(e) => set("country", e.target.value)}>
                {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Age range">
              <input
                className={inputCls}
                placeholder="25-40"
                value={form.age_range}
                onChange={(e) => set("age_range", e.target.value)}
              />
            </Field>
            <Field label="Gender">
              <select className={selectCls} value={form.gender} onChange={(e) => set("gender", e.target.value)}>
                {GENDERS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </Field>
            <Field label="Income">
              <select className={selectCls} value={form.income_level} onChange={(e) => set("income_level", e.target.value)}>
                {INCOME_LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </Field>
          </div>

          {/* Domain */}
          <Field label="Domain">
            <div className="flex gap-3 flex-wrap">
              {DOMAINS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => set("domain", d.value)}
                  className={
                    "px-4 py-2 text-xs font-mono border transition-colors " +
                    (form.domain === d.value
                      ? "border-signal text-signal"
                      : "border-parchment/15 text-static hover:border-parchment/30")
                  }
                >
                  {d.label}
                </button>
              ))}
            </div>
          </Field>

          {error && (
            <div className="border border-parchment/15 p-4">
              <p className="font-mono text-xs text-static">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={!form.business_problem.trim()}
            className="w-full py-4 font-condensed font-bold text-void bg-signal text-lg tracking-wide
                       disabled:opacity-30 disabled:cursor-not-allowed hover:bg-parchment transition-colors"
          >
            Generate persona →
          </button>
        </form>
      ) : (
        /* Generation progress */
        <div className="space-y-8">
          <div className="space-y-4">
            {steps.map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-signal font-mono text-xs shrink-0">✓</span>
                <span className="text-parchment/75 text-sm">{s}</span>
              </div>
            ))}

            {/* Animated current step */}
            {!error && (
              <div className="flex items-center gap-3">
                <span className="inline-flex gap-0.5 shrink-0">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="w-1 h-1 bg-signal"
                      style={{ animation: `pulse 1.2s ${i * 0.2}s ease-in-out infinite` }}
                    />
                  ))}
                </span>
                <span className="text-parchment/50 text-sm">Working…</span>
              </div>
            )}
          </div>

          {error && (
            <div className="border border-parchment/15 p-4">
              <p className="font-mono text-xs text-static mb-3">{error}</p>
              <button
                onClick={() => { setRunning(false); setError(""); }}
                className="text-xs font-mono text-parchment/50 hover:text-parchment transition-colors"
              >
                ← Try again
              </button>
            </div>
          )}

          <div className="border-t border-parchment/10 pt-6">
            <p className="font-mono text-[10px] text-static">
              Generation typically takes 45–90 seconds · powered by claude-sonnet
            </p>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.2; transform: scaleY(1); }
          50% { opacity: 1; transform: scaleY(1.5); }
        }
      `}</style>
    </main>
  );
}
