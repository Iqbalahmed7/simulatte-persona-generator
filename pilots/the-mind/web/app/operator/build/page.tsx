"use client";

/**
 * app/operator/build/page.tsx — Build a new prospect Twin.
 *
 * Form → POST /operator/twins (SSE stream) → redirect to /operator/[twin_id]
 *
 * SSE stages: recon (3 sub-passes) → synthesis → ready
 * Errors surface with human-readable messages from OPERATOR_ERROR_MESSAGES.
 */
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  streamBuild,
  OperatorAllowanceError,
  OPERATOR_ERROR_MESSAGES,
  type BuildSSEEvent,
} from "@/lib/operator-api";
import { useOperatorAllowance } from "@/components/OperatorAllowanceProvider";

// ── Stage progress types ──────────────────────────────────────────────────

type StageStatus = "pending" | "active" | "done" | "error";

interface StageRow {
  key: string;
  label: string;
  message: string;
  status: StageStatus;
}

const INITIAL_STAGES: StageRow[] = [
  { key: "recon",     label: "Public recon",      message: "Waiting…", status: "pending" },
  { key: "synthesis", label: "Synthesis",          message: "Waiting…", status: "pending" },
  { key: "portrait",  label: "Portrait",           message: "Waiting…", status: "pending" },
  { key: "ready",     label: "Ready",              message: "Waiting…", status: "pending" },
];

// Stage → progress bar percentage
function stageToPercent(stages: StageRow[]): number {
  const recon     = stages.find((s) => s.key === "recon")!;
  const synthesis = stages.find((s) => s.key === "synthesis")!;
  const portrait  = stages.find((s) => s.key === "portrait")!;
  const ready     = stages.find((s) => s.key === "ready")!;
  if (ready.status === "done")     return 100;
  if (portrait.status === "active") return 75;
  if (portrait.status === "done")  return 88;
  if (synthesis.status === "active") return 50;
  if (synthesis.status === "done") return 65;
  if (recon.status === "active")   return 20;
  if (recon.status === "done")     return 40;
  return 0;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ── Stage indicator dot ───────────────────────────────────────────────────

function StageDot({ status }: { status: StageStatus }) {
  if (status === "active") {
    return (
      <span className="w-2 h-2 rounded-full bg-signal animate-pulse flex-shrink-0" />
    );
  }
  if (status === "done") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2.5" strokeLinecap="round" className="text-signal flex-shrink-0">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    );
  }
  if (status === "error") {
    return <span className="w-2 h-2 rounded-full bg-red-400/60 flex-shrink-0" />;
  }
  return <span className="w-2 h-2 rounded-full bg-parchment/15 flex-shrink-0" />;
}

// ── Build progress strip ──────────────────────────────────────────────────

function BuildProgress({
  stages,
  error,
  elapsed,
  completedIn,
}: {
  stages: StageRow[];
  error: string | null;
  elapsed: number;
  completedIn: number | null;
}) {
  const pct = stageToPercent(stages);
  const isActive = stages.some((s) => s.status === "active");
  const isDone = completedIn !== null;

  return (
    <div className="mt-6 border border-parchment/10 p-4 space-y-3">
      {/* Header row: label + elapsed / completed */}
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-mono text-signal uppercase tracking-[0.18em]">
          Build progress
        </p>
        <span className="text-[10px] font-mono text-static">
          {isDone
            ? `Completed in ${formatElapsed(completedIn)}`
            : elapsed > 0
            ? `${formatElapsed(elapsed)} elapsed`
            : null}
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative h-px bg-parchment/10 overflow-hidden mb-3">
        <div
          className="h-px bg-signal transition-all duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
        {/* Shimmer sweep while active */}
        {isActive && (
          <div
            className="absolute inset-y-0 w-24 bg-gradient-to-r from-transparent via-signal/40 to-transparent"
            style={{ animation: "shimmer 1.8s ease-in-out infinite" }}
          />
        )}
      </div>

      {stages.map((s) => (
        <div key={s.key} className="flex items-start gap-3">
          <div className="mt-0.5">
            <StageDot status={s.status} />
          </div>
          <div className="flex-1 min-w-0">
            <p className={`text-xs font-mono ${
              s.status === "active" ? "text-parchment" :
              s.status === "done" ? "text-parchment/60" :
              "text-static"
            }`}>
              {s.label}
            </p>
            <p className={`text-[11px] font-mono mt-0.5 truncate ${
              s.status === "active" ? "text-static" : "text-parchment/25"
            }`}>
              {s.message}
            </p>
          </div>
        </div>
      ))}
      {error && (
        <div className="mt-3 border-t border-parchment/10 pt-3">
          <p className="text-red-400 text-xs font-mono">{error}</p>
        </div>
      )}

      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-96px); }
          100% { transform: translateX(calc(100vw + 96px)); }
        }
      `}</style>
    </div>
  );
}

// ── Field ─────────────────────────────────────────────────────────────────

function Field({
  label,
  hint,
  required,
  value,
  onChange,
  disabled,
  placeholder,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1.5 text-xs font-mono text-parchment/70 uppercase tracking-widest">
        {label}
        {required && <span className="text-signal">*</span>}
      </label>
      {hint && <p className="text-[11px] font-mono text-static">{hint}</p>}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="w-full bg-transparent border border-parchment/15 focus:border-parchment/35 px-3 py-2.5 text-sm font-mono text-parchment placeholder:text-parchment/20 outline-none transition-colors disabled:opacity-40"
      />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function BuildPage() {
  const router = useRouter();
  const { triggerOperatorAllowanceExceeded } = useOperatorAllowance();
  const abortRef = useRef<AbortController | null>(null);
  const startTimeRef = useRef<number | null>(null);

  const [fullName, setFullName] = useState("");
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [building, setBuilding] = useState(false);
  const [stages, setStages] = useState<StageRow[]>(INITIAL_STAGES);
  const [buildError, setBuildError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [completedIn, setCompletedIn] = useState<number | null>(null);

  // Tick elapsed timer while building
  useEffect(() => {
    if (!building) return;
    setElapsed(0);
    startTimeRef.current = Date.now();
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - (startTimeRef.current ?? Date.now())) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [building]);

  function updateStage(
    key: string,
    patch: Partial<Pick<StageRow, "status" | "message">>
  ) {
    setStages((prev) =>
      prev.map((s) => (s.key === key ? { ...s, ...patch } : s))
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim() || building) return;

    setBuilding(true);
    setBuildError(null);
    setCompletedIn(null);
    setStages(INITIAL_STAGES);

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      await streamBuild(
        {
          full_name: fullName.trim(),
          company: company.trim() || undefined,
          title: title.trim() || undefined,
        },
        (evt: BuildSSEEvent) => {
          if (evt.stage === "recon") {
            updateStage("recon", {
              status: "active",
              message: evt.message ?? "Searching public sources…",
            });
          } else if (evt.stage === "synthesis") {
            updateStage("recon", { status: "done", message: "Done" });
            updateStage("synthesis", {
              status: "active",
              message: evt.message ?? "Building decision filter…",
            });
          } else if (evt.stage === "portrait") {
            updateStage("synthesis", { status: "done", message: "Done" });
            updateStage("portrait", {
              status: "active",
              message: evt.message ?? "Generating portrait…",
            });
          } else if (evt.stage === "ready") {
            updateStage("portrait", { status: "done", message: "Done" });
            updateStage("ready", { status: "done", message: "Twin ready" });
            // Capture final elapsed before clearing building state
            const finalElapsed = Math.floor(
              (Date.now() - (startTimeRef.current ?? Date.now())) / 1000
            );
            setCompletedIn(finalElapsed);
            setBuilding(false);
            if (evt.twin_id) {
              // Brief delay so user sees "100%" and completed time before redirect
              setTimeout(() => router.push(`/operator/${evt.twin_id}`), 1200);
            }
          } else if (evt.stage === "error") {
            const code = evt.error_code ?? "";
            const msg =
              OPERATOR_ERROR_MESSAGES[code] ??
              evt.error ??
              "Build failed — please try again.";
            setBuildError(msg);
            setStages((prev) =>
              prev.map((s) =>
                s.status === "active" ? { ...s, status: "error" } : s
              )
            );
            setBuilding(false);
          }
        },
        abort.signal
      );
    } catch (err) {
      if (err instanceof OperatorAllowanceError) {
        triggerOperatorAllowanceExceeded(err.payload);
        setBuilding(false);
        setStages(INITIAL_STAGES);
        return;
      }
      if ((err as Error).name === "AbortError") {
        setBuildError("Build cancelled.");
      } else {
        setBuildError((err as Error).message ?? "Build failed — please try again.");
      }
      setStages((prev) =>
        prev.map((s) =>
          s.status === "active" ? { ...s, status: "error" } : s
        )
      );
      setBuilding(false);
    }
  }

  function handleCancel() {
    abortRef.current?.abort();
    setBuilding(false);
    setStages(INITIAL_STAGES);
    setBuildError(null);
    setElapsed(0);
    setCompletedIn(null);
  }

  const canSubmit = fullName.trim().length >= 2 && !building;
  const showProgress =
    building ||
    completedIn !== null ||
    buildError !== null ||
    stages.some((s) => s.status !== "pending");

  return (
    <div className="min-h-screen bg-void px-4 py-8">
      <div className="max-w-[480px] mx-auto">
        {/* Back */}
        <Link
          href="/operator"
          className="inline-flex items-center gap-1.5 text-[11px] font-mono text-static hover:text-parchment/60 transition-colors mb-8"
        >
          ← Back to Twins
        </Link>

        {/* Header */}
        <div className="mb-8">
          <p className="text-[10px] font-mono text-signal uppercase tracking-[0.18em] mb-1">
            The Operator
          </p>
          <h1 className="font-condensed font-black text-parchment text-3xl uppercase tracking-wide">
            Build a Twin
          </h1>
          <p className="text-static text-sm font-mono mt-2 leading-relaxed">
            A probabilistic decision-filter model built from public signal.
            Not the person — a structured approximation for sales prep.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <Field
            label="Full name"
            required
            value={fullName}
            onChange={setFullName}
            disabled={building}
            placeholder="e.g. Priya Sharma"
          />
          <Field
            label="Company"
            hint="Improves recon precision"
            value={company}
            onChange={setCompany}
            disabled={building}
            placeholder="e.g. Zomato"
          />
          <Field
            label="Title / role"
            value={title}
            onChange={setTitle}
            disabled={building}
            placeholder="e.g. VP Marketing"
          />

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={!canSubmit}
              className="flex-1 px-4 py-3 bg-signal/10 hover:bg-signal/20 border border-signal/30 text-signal text-sm font-mono transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {building ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
                  Building…
                </span>
              ) : (
                "Build Twin"
              )}
            </button>
            {building && (
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-3 border border-parchment/15 text-parchment/40 hover:text-parchment/70 text-sm font-mono transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </form>

        {/* Progress strip — shown once build starts */}
        {showProgress && stages.some((s) => s.status !== "pending") && (
          <BuildProgress
            stages={stages}
            error={buildError}
            elapsed={elapsed}
            completedIn={completedIn}
          />
        )}

        {/* Disclaimer */}
        <p className="mt-8 text-[11px] font-mono text-parchment/20 leading-relaxed">
          Twins are built from publicly available information. EU-based
          subjects are not supported in Phase 1. All outputs are
          probabilistic — treat as pre-call hypothesis, not fact.
        </p>
      </div>
    </div>
  );
}
