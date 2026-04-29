"use client";

import { useState } from "react";

interface ClaimVerdict {
  claim?: string;
  score?: number | string;
  comment?: string;
  // Many shapes are possible — render whatever is useful.
  [k: string]: unknown;
}

interface ProbePayload {
  claims_verdict?: ClaimVerdict[];
  claim_verdicts?: ClaimVerdict[];
  verdicts?: ClaimVerdict[];
  [k: string]: unknown;
}

export default function ProbeEventActions({ probeId }: { probeId: string }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [verdicts, setVerdicts] = useState<ClaimVerdict[] | null>(null);

  async function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (verdicts !== null) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/probes/${encodeURIComponent(probeId)}/full`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: ProbePayload = await res.json();
      const list =
        json.claims_verdict ?? json.claim_verdicts ?? json.verdicts ?? [];
      setVerdicts(Array.isArray(list) ? list : []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-2">
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={toggle}
          className="text-signal text-[11px] font-mono uppercase tracking-widest hover:text-parchment transition-colors"
        >
          {open ? "Hide verdicts" : "View verdicts"}
        </button>
        <a
          href={`/api/probes/${encodeURIComponent(probeId)}/download`}
          download
          className="text-signal text-[11px] font-mono uppercase tracking-widest hover:text-parchment transition-colors"
        >
          Download
        </a>
      </div>
      {open && (
        <div className="mt-3 border border-parchment/10 p-3 bg-void/40">
          {loading && (
            <p className="font-mono text-[11px] text-parchment/50">Loading…</p>
          )}
          {error && (
            <p className="font-mono text-[11px] text-static">{error}</p>
          )}
          {verdicts && verdicts.length === 0 && !loading && !error && (
            <p className="font-mono text-[11px] text-parchment/50">
              No claim verdicts in payload.
            </p>
          )}
          {verdicts && verdicts.length > 0 && (
            <ul className="space-y-2">
              {verdicts.map((v, i) => (
                <li
                  key={i}
                  className="font-mono text-[11px] text-parchment/80 flex flex-col gap-0.5"
                >
                  <span>
                    <span className="text-parchment">{String(v.claim ?? `claim ${i + 1}`)}</span>
                    {v.score !== undefined && (
                      <span className="ml-2 text-signal">· {String(v.score)}</span>
                    )}
                  </span>
                  {v.comment && (
                    <span className="text-parchment/55 italic">
                      {String(v.comment)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
