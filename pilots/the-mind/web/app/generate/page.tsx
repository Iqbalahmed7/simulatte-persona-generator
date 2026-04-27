"use client";

/**
 * /generate — Persona generation page.
 *
 * Two modes:
 *   1. Wizard (default) — chip-only steps, max 1 line of optional typing.
 *      Composes a coherent brief from selections; non-intrusive.
 *   2. Free brief — original textarea + PDF upload (power users).
 *
 * Both routes call the same `generatePersona` SSE endpoint.
 */
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { generatePersona, ICPForm, GenerationEvent } from "@/lib/api";
import PersonaWizard from "@/components/PersonaWizard";

export default function GeneratePage() {
  const router = useRouter();
  const [mode, setMode] = useState<"wizard" | "free">("wizard");
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [error, setError] = useState("");

  async function runGeneration(form: ICPForm) {
    setRunning(true);
    setSteps([]);
    setError("");

    let navigated = false;
    const timeoutId = setTimeout(() => {
      if (!navigated) {
        setError("Generation timed out — the server took too long. Please try again.");
        setRunning(false);
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
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      clearTimeout(timeoutId);
      if (!navigated) setRunning(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-8 md:px-6 md:py-12 max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Back
        </Link>
        <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mt-6 mb-3">
          Simulatte / Generate
        </p>
        <h1 className="font-condensed font-bold text-parchment leading-none mb-3"
            style={{ fontSize: "clamp(36px,5vw,60px)" }}>
          Simulate a <span className="text-signal">person.</span>
        </h1>
        <p className="text-parchment/60 text-base">
          Pick a few traits — we&apos;ll build a behaviourally coherent person with 200+ attributes and full decision psychology.
        </p>
      </div>

      {!running ? (
        <>
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
                <span className="text-signal font-mono text-xs shrink-0">✓</span>
                <span className="text-parchment/75 text-sm">{s}</span>
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
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-mono text-static uppercase tracking-widest">
          Free brief
        </p>
        <button
          type="button"
          onClick={onSwitchToWizard}
          className="text-[11px] font-mono text-parchment/50 hover:text-signal transition-colors"
        >
          ← Use the wizard
        </button>
      </div>

      <div>
        <label className="block text-[11px] font-sans font-semibold tracking-widest uppercase text-static mb-2">
          Who do you want to simulate?
        </label>
        <p className="text-xs text-parchment/40 mb-3">
          Be as specific or broad as you like — age, family, job, city, personality, values, habits.
        </p>
        <textarea
          className="w-full bg-transparent border border-parchment/15 px-4 py-3 text-sm text-parchment
                     placeholder-parchment/20 focus:outline-none focus:border-parchment/40 transition-colors resize-none"
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
          className={`border border-dashed px-6 py-8 text-center cursor-pointer transition-colors
            ${dragging ? "border-parchment/40 bg-parchment/5" : "border-parchment/15 hover:border-parchment/30"}`}
        >
          {pdfFile ? (
            <div className="flex items-center justify-center gap-3">
              <span className="font-mono text-xs text-signal">↑ {pdfFile.name}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setPdfFile(null); }}
                className="text-[10px] font-mono text-static hover:text-parchment/50"
              >
                remove
              </button>
            </div>
          ) : (
            <>
              <p className="text-parchment/40 text-sm">Drop a PDF here, or click to browse</p>
              <p className="text-[11px] font-mono text-static mt-1">PDF only · max 10 MB</p>
            </>
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
                "px-4 py-2 text-xs font-mono border transition-colors " +
                (domain === d.value
                  ? "border-signal text-signal"
                  : "border-parchment/15 text-static hover:border-parchment/30")
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
        className="w-full py-4 font-condensed font-bold text-void bg-signal text-lg tracking-wide
                   disabled:opacity-30 disabled:cursor-not-allowed hover:bg-parchment transition-colors"
      >
        Simulate this person →
      </button>
    </form>
  );
}
