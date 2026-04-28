"use client";

/**
 * /generate — Persona generation page.
 *
 * Two modes (tabbed, free-brief is primary):
 *   1. Free brief (default) — natural-language textarea + optional PDF.
 *      The expressive surface; what most people will use.
 *   2. Wizard — chip-only stepper for users who'd rather pick than type.
 *      Same SSE endpoint, just a different way to build the brief.
 */
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { generatePersona, ICPForm, GenerationEvent } from "@/lib/api";
import PersonaWizard from "@/components/PersonaWizard";
import AccessGate from "@/components/AccessGate";

export default function GeneratePage() {
  return (
    <AccessGate>
      <GeneratePageInner />
    </AccessGate>
  );
}

function GeneratePageInner() {
  const router = useRouter();
  const [mode, setMode] = useState<"wizard" | "free">("free");
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [error, setError] = useState("");
  // Aborts the in-flight SSE stream when the user navigates away mid-
  // generation. Without this, the read loop and the (already-charged)
  // allowance increment continue in the background after unmount.
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  async function runGeneration(form: ICPForm) {
    setRunning(true);
    setSteps([]);
    setError("");

    // Cancel any prior run before starting a new one.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    let navigated = false;
    const timeoutId = setTimeout(() => {
      if (!navigated) {
        setError("Generation timed out — the server took too long. Please try again.");
        setRunning(false);
        controller.abort();
      }
    }, 180_000);

    try {
      await generatePersona(form, (event: GenerationEvent) => {
        if (event.type === "status" && event.message) {
          setSteps((prev) => [...prev, event.message!]);
        }
        if (event.type === "result" && event.persona_id) {
          navigated = true;
          clearTimeout(timeoutId);
          router.push(`/persona/${event.persona_id}`);
        }
        if (event.type === "error" && event.message) {
          setError(event.message);
        }
      }, controller.signal);
    } catch (err: unknown) {
      // AbortError is intentional (unmount or timeout) — don't show as error.
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      clearTimeout(timeoutId);
      if (!navigated) setRunning(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-8 md:px-6 md:py-12 max-w-2xl mx-auto pb-[max(7rem,env(safe-area-inset-bottom)+5rem)] sm:pb-0">
      {/* Header */}
      <div className="mb-10">
        <Link href="/dashboard" className="inline-flex items-center min-h-[44px] text-sm font-mono text-parchment/70 active:text-parchment transition-colors">
          ← Back
        </Link>
        <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mt-6 mb-3">
          Simulatte / Generate
        </p>
        <h1 className="font-condensed font-bold text-parchment leading-none mb-3"
            style={{ fontSize: "clamp(36px,5vw,60px)" }}>
          Simulate a <span className="text-signal">person.</span>
        </h1>
        <p className="text-parchment/75 text-base leading-relaxed">
          Describe the person you want to simulate, in your own words. Or use the wizard if you&apos;d rather pick than type.
        </p>
      </div>

      {!running ? (
        <>
          {/* Mode tab strip — free brief is primary, wizard is secondary */}
          <div className="flex gap-2 mb-8 border-b border-parchment/10">
            <button
              onClick={() => setMode("free")}
              className={`px-5 min-h-[44px] py-3 text-base font-medium tracking-wide transition-colors border-b-2 -mb-px
                ${mode === "free"
                  ? "border-signal text-parchment"
                  : "border-transparent text-parchment/45 hover:text-parchment/70"}`}
            >
              Write your own
            </button>
            <button
              onClick={() => setMode("wizard")}
              className={`px-5 min-h-[44px] py-3 text-base font-medium tracking-wide transition-colors border-b-2 -mb-px
                ${mode === "wizard"
                  ? "border-signal text-parchment"
                  : "border-transparent text-parchment/45 hover:text-parchment/70"}`}
            >
              Use the wizard
            </button>
          </div>

          {mode === "wizard" ? (
            <PersonaWizard
              onSubmit={runGeneration}
              onSwitchToFree={() => setMode("free")}
              error={error}
            />
          ) : (
            <FreeBriefForm
              onSubmit={runGeneration}
              onSwitchToWizard={() => setMode("wizard")}
              error={error}
            />
          )}
        </>
      ) : (
        <div className="space-y-8">
          <div className="space-y-4">
            {steps.map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-signal font-mono text-sm shrink-0">✓</span>
                <span className="text-parchment/85 text-base break-words min-w-0">{s}</span>
              </div>
            ))}
            {!error && (
              <div className="flex items-center gap-3">
                <span className="inline-flex gap-0.5 shrink-0">
                  {[0, 1, 2].map((i) => (
                    <span key={i} className="w-1 h-1 bg-signal"
                      style={{ animation: `pulse 1.2s ${i * 0.2}s ease-in-out infinite` }} />
                  ))}
                </span>
                <span className="text-parchment/70 text-base">Working…</span>
              </div>
            )}
          </div>

          {error && (
            <div className="border border-amber-400/40 bg-amber-400/[0.04] p-5">
              <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-amber-400/80 mb-2">
                Couldn&#x2019;t generate
              </p>
              <p className="text-parchment text-base mb-4 leading-relaxed">{error}</p>
              <button
                onClick={() => { setRunning(false); setError(""); }}
                className="min-h-[44px] inline-flex items-center text-sm font-mono uppercase tracking-widest text-parchment/80 active:text-signal transition-colors"
              >
                ← Try again
              </button>
            </div>
          )}

          <div className="border-t border-parchment/10 pt-6">
            <p className="font-mono text-[10px] text-static">
              Generation typically takes 45–90 seconds · powered by Simulatte&apos;s Mind — Deep Persona Generator
            </p>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.2; transform: scaleY(1); }
          50%       { opacity: 1;   transform: scaleY(1.5); }
        }
      `}</style>
    </main>
  );
}

/* ─────────────────── Free-brief fallback (original form) ─────────────────── */

const DOMAINS = [
  { value: "cpg", label: "Consumer Goods" },
  { value: "saas", label: "SaaS / Tech" },
  { value: "health_wellness", label: "Health & Wellness" },
];

const PLACEHOLDER =
  "A 44-year-old mother of three in suburban Chicago. Upper-middle income, works part-time as an occupational therapist. Health-conscious, reads labels, distrusts influencers.";

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(",")[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function FreeBriefForm({
  onSubmit,
  onSwitchToWizard,
  error,
}: {
  onSubmit: (form: ICPForm) => void;
  onSwitchToWizard: () => void;
  error: string;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [brief, setBrief] = useState("");
  const [domain, setDomain] = useState("cpg");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file?.type === "application/pdf") setPdfFile(file);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file?.type === "application/pdf") setPdfFile(file);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!brief.trim() && !pdfFile) return;
    setSubmitting(true);
    let pdf_content: string | undefined;
    if (pdfFile) {
      try {
        pdf_content = await toBase64(pdfFile);
      } catch {
        setSubmitting(false);
        return;
      }
    }
    onSubmit({ brief: brief.trim(), domain, pdf_content });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-[11px] font-sans font-semibold tracking-widest uppercase text-static mb-2">
          Who do you want to simulate?
        </label>
        <p className="text-sm text-parchment/70 mb-3">
          Be as specific or broad as you like — age, family, job, city, personality, values, habits.
        </p>
        <textarea
          className="w-full bg-transparent border border-parchment/15 px-4 py-3 text-base text-parchment
                     placeholder-parchment/30 focus:outline-none focus:border-parchment/40 transition-colors resize-none"
          style={{ fontSize: "16px" }}
          rows={6}
          placeholder={PLACEHOLDER}
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
        />
      </div>

      <div>
        <label className="block text-[11px] font-sans font-semibold tracking-widest uppercase text-static mb-2">
          Upload a brief <span className="text-parchment/30 normal-case font-normal">— optional</span>
        </label>
        <div
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleFileDrop}
          className={`border border-dashed px-6 py-8 text-center cursor-pointer transition-colors min-h-[88px] flex items-center justify-center
            ${dragging ? "border-parchment/40 bg-parchment/5" : "border-parchment/15 hover:border-parchment/30"}`}
        >
          {pdfFile ? (
            <div className="flex items-center justify-center gap-3 min-w-0 w-full">
              <span className="font-mono text-sm text-signal truncate">↑ {pdfFile.name}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setPdfFile(null); }}
                className="text-sm font-mono text-parchment/70 active:text-parchment min-h-[44px] px-3 shrink-0"
              >
                remove
              </button>
            </div>
          ) : (
            <div>
              <p className="text-parchment/75 text-base">Tap to upload a PDF</p>
              <p className="text-sm font-mono text-parchment/70 mt-1">PDF only · max 10 MB</p>
            </div>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      <div>
        <label className="block text-[11px] font-sans font-semibold tracking-widest uppercase text-static mb-2">
          Domain context
        </label>
        <div className="flex gap-2 flex-wrap">
          {DOMAINS.map((d) => (
            <button
              key={d.value}
              type="button"
              onClick={() => setDomain(d.value)}
              className={
                "px-4 min-h-[44px] py-2 text-sm font-mono border transition-colors " +
                (domain === d.value
                  ? "border-signal text-signal"
                  : "border-parchment/15 text-parchment/70 active:border-parchment/40")
              }
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="border border-parchment/15 p-4">
          <p className="font-mono text-xs text-static">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={(!brief.trim() && !pdfFile) || submitting}
        className="w-full min-h-[52px] py-4 font-condensed font-bold text-void bg-signal text-lg tracking-wide
                   disabled:opacity-30 disabled:cursor-not-allowed active:bg-parchment transition-colors"
      >
        Simulate this person →
      </button>
    </form>
  );
}
