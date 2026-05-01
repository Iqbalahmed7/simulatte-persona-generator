"use client";

/**
 * app/operator/build/page.tsx — Build a new prospect Twin.
 *
 * Form → POST /operator/twins (SSE stream) → redirect to /operator/[twin_id]
 *
 * SSE stages: recon (3 sub-passes) → synthesis → ready
 * Errors surface with human-readable messages from OPERATOR_ERROR_MESSAGES.
 */
import { useRef, useState } from "react";
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
  { key: "recon", label: "Public recon", message: "Waiting…", status: "pending" },
  { key: "synthesis", label: "Synthesis", message: "Waiting…", status: "pending" },
  { key: "ready", label: "Ready", message: "Waiting…", status: "pending" },
];

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
}: {
  stages: StageRow[];
  error: string | null;
}) {
  return (
    <div className="mt-6 border border-parchment/10 p-4 space-y-3">
      <p className="text-[10px] font-mono text-signal uppercase tracking-[0.18em] mb-2">
        Build progress
      </p>
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

  const [fullName, setFullName] = useState("");
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [building, setBuilding] = useState(false);
  const [stages, setStages] = useState<StageRow[]>(INITIAL_STAGES);
  const [buildError, setBuildError] = useState<string | null>(null);

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
          } else if (evt.stage === "ready") {
            updateStage("synthesis", { status: "done", message: "Done" });
            updateStage("ready", { status: "done", message: "Twin ready" });
            if (evt.twin_id) {
              router.push(`/operator/${evt.twin_id}`);
            }
          } else if (evt.stage === "error") {
            const code = evt.error_code ?? "";
            const msg =
              OPERATOR_ERROR_MESSAGES[code] ??
              evt.error ??
              "Build failed — please try again.";
            setBuildError(msg);
            // Mark whichever stage was active as errored
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
  }

  const canSubmit = fullName.trim().length >= 2 && !building;

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
        {(building || buildError || stages.some((s) => s.status !== "pending")) &&
          stages.some((s) => s.status !== "pending") && (
            <BuildProgress stages={stages} error={buildError} />
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
