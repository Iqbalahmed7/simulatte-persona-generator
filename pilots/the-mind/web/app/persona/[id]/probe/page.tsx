"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchGeneratedPersona, runProbe, GeneratedPersona } from "@/lib/api";

const CATEGORIES = [
  "Consumer electronics",
  "Food & beverage",
  "Health & wellness",
  "Fashion & apparel",
  "Home & living",
  "Beauty & personal care",
  "Financial services",
  "Software / SaaS",
  "Mobility & transport",
  "Education & learning",
  "Entertainment & media",
  "Travel & hospitality",
  "Other",
];

const STATUS_STEPS = (firstName: string, category: string) => [
  `Recalling ${firstName}'s memories of ${category}...`,
  `Showing ${firstName} the product...`,
  `Asking ${firstName} 8 questions...`,
  "Assembling verdict...",
];

export default function ProbePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [persona, setPersona] = useState<GeneratedPersona | null>(null);
  const [personaError, setPersonaError] = useState("");

  const [productName, setProductName] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [description, setDescription] = useState("");
  const [claims, setClaims] = useState<string[]>([""]);
  const [price, setPrice] = useState("");
  const [imageUrl, setImageUrl] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [statusStep, setStatusStep] = useState(0);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    fetchGeneratedPersona(id)
      .then(setPersona)
      .catch((e: unknown) =>
        setPersonaError(e instanceof Error ? e.message : "Failed to load persona")
      );
  }, [id]);

  const firstName = persona?.narrative?.display_name || persona?.demographic_anchor?.name?.split(" ")[0] || "them";
  const steps = STATUS_STEPS(firstName, category);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!productName.trim() || !description.trim()) return;
    if (description.length < 50) {
      setSubmitError("Description must be at least 50 characters.");
      return;
    }
    setSubmitError("");
    setSubmitting(true);
    setStatusStep(0);
    setStatusMsg(steps[0]);

    // Advance status messages on a timer while we wait
    const interval = setInterval(() => {
      setStatusStep((s) => {
        const next = Math.min(s + 1, steps.length - 1);
        setStatusMsg(steps[next]);
        return next;
      });
    }, 6000);

    try {
      const result = await runProbe(id, {
        product_name: productName.trim(),
        category,
        description: description.trim(),
        claims: claims.filter((c) => c.trim()).slice(0, 5),
        price: price.trim(),
        image_url: imageUrl.trim() || undefined,
      });
      clearInterval(interval);
      router.push(`/persona/${id}/probe/${result.probe_id}`);
    } catch (err: unknown) {
      clearInterval(interval);
      setSubmitError(err instanceof Error ? err.message : "Probe failed. Please try again.");
      setSubmitting(false);
      setStatusMsg("");
    }
  }

  function addClaim() {
    if (claims.length < 5) setClaims([...claims, ""]);
  }

  function updateClaim(i: number, val: string) {
    const next = [...claims];
    next[i] = val;
    setClaims(next);
  }

  function removeClaim(i: number) {
    setClaims(claims.filter((_, idx) => idx !== i));
  }

  if (personaError) {
    return (
      <main className="min-h-screen px-6 py-12 max-w-2xl mx-auto">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Home
        </Link>
        <div className="mt-12 border border-parchment/10 p-6">
          <p className="font-mono text-sm text-static">{personaError}</p>
        </div>
      </main>
    );
  }

  if (!persona) {
    return (
      <main className="min-h-screen px-6 py-12 flex items-center justify-center">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 bg-signal"
              style={{ animation: `dot-pulse 1.2s ${i * 0.2}s ease-in-out infinite` }} />
          ))}
        </div>
        <style>{`@keyframes dot-pulse { 0%,100%{opacity:.2} 50%{opacity:1} }`}</style>
      </main>
    );
  }

  const da = persona.demographic_anchor;

  if (submitting) {
    return (
      <main className="min-h-screen px-6 py-12 flex flex-col items-center justify-center gap-8">
        <div className="text-center">
          <p className="text-[11px] font-mono text-static uppercase tracking-widest mb-4">
            Running Litmus Probe
          </p>
          <h2 className="font-condensed font-bold text-parchment mb-2"
            style={{ fontSize: "clamp(24px,3vw,36px)" }}>
            {productName}
          </h2>
          <p className="text-static text-sm mb-10">Testing against {da.name}</p>
          <div className="flex gap-1.5 justify-center mb-6">
            {[0, 1, 2].map((i) => (
              <span key={i} className="w-2 h-2 bg-signal"
                style={{ animation: `dot-pulse 1.2s ${i * 0.2}s ease-in-out infinite` }} />
            ))}
          </div>
          <p className="font-mono text-[11px] text-static">{statusMsg}</p>
          <div className="mt-6 flex gap-1 justify-center">
            {steps.map((_, i) => (
              <div key={i} className={`h-px w-8 transition-all ${i <= statusStep ? "bg-signal" : "bg-parchment/10"}`} />
            ))}
          </div>
        </div>
        <style>{`@keyframes dot-pulse { 0%,100%{opacity:.2} 50%{opacity:1} }`}</style>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-6 md:py-12 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-10">
        <Link href={`/persona/${id}`} className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Back to {da.name}
        </Link>
        <span className="font-mono text-[10px] text-static">{id}</span>
      </div>

      <div className="mb-8">
        <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-2">
          Litmus Probe
        </p>
        <h1 className="font-condensed font-bold text-parchment leading-none mb-2"
          style={{ fontSize: "clamp(28px,4vw,48px)" }}>
          Test a product with {firstName}
        </h1>
        <p className="text-parchment/60 text-sm">
          {da.name} &middot; {da.age} &middot; {da.location.city}, {da.location.country}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Product name */}
        <div>
          <label className="block text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Product name <span className="text-signal">*</span>
          </label>
          <input
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            required
            maxLength={120}
            placeholder="e.g. SleepScore Pro"
            className="w-full bg-transparent border border-parchment/20 px-4 py-3 text-sm text-parchment placeholder-static/40 focus:outline-none focus:border-signal transition-colors"
          />
        </div>

        {/* Category */}
        <div>
          <label className="block text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Category <span className="text-signal">*</span>
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-void border border-parchment/20 px-4 py-3 text-sm text-parchment focus:outline-none focus:border-signal transition-colors"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Description <span className="text-signal">*</span>
            <span className="ml-2 text-static/50 normal-case tracking-normal">50–2000 chars</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            minLength={50}
            maxLength={2000}
            rows={5}
            placeholder="Describe the product: what it does, who it's for, key benefits, how it works..."
            className="w-full bg-transparent border border-parchment/20 px-4 py-3 text-sm text-parchment placeholder-static/40 focus:outline-none focus:border-signal transition-colors resize-none"
          />
          <p className="text-[10px] font-mono text-static mt-1 text-right">{description.length}/2000</p>
        </div>

        {/* Claims */}
        <div>
          <label className="block text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Product claims
            <span className="ml-2 text-static/50 normal-case tracking-normal">up to 5</span>
          </label>
          <div className="space-y-2">
            {claims.map((claim, i) => (
              <div key={i} className="flex gap-2">
                <input
                  type="text"
                  value={claim}
                  onChange={(e) => updateClaim(i, e.target.value)}
                  maxLength={200}
                  placeholder={`Claim ${i + 1} — e.g. "Clinically proven to improve sleep by 40%"`}
                  className="flex-1 bg-transparent border border-parchment/20 px-4 py-2.5 text-sm text-parchment placeholder-static/40 focus:outline-none focus:border-signal transition-colors"
                />
                {claims.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeClaim(i)}
                    className="px-3 text-static hover:text-parchment/50 font-mono text-sm transition-colors border border-parchment/10 hover:border-parchment/20"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
          {claims.length < 5 && (
            <button
              type="button"
              onClick={addClaim}
              className="mt-2 text-[10px] font-mono text-static hover:text-parchment/50 transition-colors uppercase tracking-widest"
            >
              + Add claim
            </button>
          )}
        </div>

        {/* Price */}
        <div>
          <label className="block text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Price
          </label>
          <input
            type="text"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            maxLength={60}
            placeholder="e.g. ₹4,999 or $49/mo"
            className="w-full bg-transparent border border-parchment/20 px-4 py-3 text-sm text-parchment placeholder-static/40 focus:outline-none focus:border-signal transition-colors"
          />
        </div>

        {/* Image URL */}
        <div>
          <label className="block text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Product image URL
            <span className="ml-2 text-static/50 normal-case tracking-normal">optional</span>
          </label>
          <input
            type="url"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            placeholder="https://..."
            className="w-full bg-transparent border border-parchment/20 px-4 py-3 text-sm text-parchment placeholder-static/40 focus:outline-none focus:border-signal transition-colors"
          />
        </div>

        {submitError && (
          <p className="font-mono text-[11px] text-red-400 border border-red-400/20 px-4 py-3">
            {submitError}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || !productName.trim() || description.length < 50}
          className="w-full bg-signal text-void font-condensed font-bold px-6 py-4 hover:bg-signal/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="text-sm tracking-widest uppercase">
            Run Litmus Probe &rarr;
          </span>
        </button>
        <p className="text-[10px] font-mono text-static text-center">
          ~20 seconds &middot; 8 questions &middot; Reaction / Belief / Friction / Commitment
        </p>
      </form>
    </main>
  );
}
