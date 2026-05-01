"use client";

import { useState } from "react";

interface AllowanceState {
  user_id:        string;
  week_starting:  string;
  twins_built:    number;
  twin_refreshes: number;
  probe_messages: number;
  frame_scores:   number;
  limits: {
    twin_build:    number;
    twin_refresh:  number;
    probe_message: number;
    frame_score:   number;
  };
}

interface Props {
  userId:  string;
  initial: AllowanceState | null;
}

interface FieldDef {
  key:   keyof Pick<AllowanceState, "twins_built" | "twin_refreshes" | "probe_messages" | "frame_scores">;
  label: string;
  limitKey: keyof AllowanceState["limits"];
}

const FIELDS: FieldDef[] = [
  { key: "twins_built",    label: "Twins built",    limitKey: "twin_build"    },
  { key: "twin_refreshes", label: "Twin refreshes", limitKey: "twin_refresh"  },
  { key: "probe_messages", label: "Probe messages", limitKey: "probe_message" },
  { key: "frame_scores",   label: "Frame scores",   limitKey: "frame_score"   },
];

export default function OperatorLimitsForm({ userId, initial }: Props) {
  const [values, setValues] = useState<Record<string, number>>(() => ({
    twins_built:    initial?.twins_built    ?? 0,
    twin_refreshes: initial?.twin_refreshes ?? 0,
    probe_messages: initial?.probe_messages ?? 0,
    frame_scores:   initial?.frame_scores   ?? 0,
  }));
  const limits = initial?.limits ?? { twin_build: 5, twin_refresh: 10, probe_message: 100, frame_score: 50 };

  const [saving, setSaving] = useState(false);
  const [saved,  setSaved]  = useState(false);
  const [error,  setError]  = useState<string | null>(null);

  function handleChange(key: string, raw: string) {
    const n = parseInt(raw, 10);
    if (!isNaN(n) && n >= 0) setValues((v) => ({ ...v, [key]: n }));
  }

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const res = await fetch(`/api/admin/operator/users/${userId}/allowance`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? body.error ?? `Error ${res.status}`);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    setValues({ twins_built: 0, twin_refreshes: 0, probe_messages: 0, frame_scores: 0 });
  }

  return (
    <div className="border border-white/8 bg-white/2 p-5 space-y-5">
      <p className="text-static text-[10px] font-mono uppercase tracking-wider">
        Current week counters — set to override usage
      </p>

      <div className="space-y-3">
        {FIELDS.map(({ key, label, limitKey }) => {
          const used  = values[key] ?? 0;
          const limit = limits[limitKey] ?? 0;
          const pct   = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
          const atLimit = used >= limit;

          return (
            <div key={key} className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-parchment text-xs font-medium">{label}</label>
                <span className={`text-xs font-mono ${atLimit ? "text-red-400" : "text-static"}`}>
                  {used} / {limit}
                </span>
              </div>
              {/* Progress bar */}
              <div className="h-1 bg-white/8 w-full">
                <div
                  className={`h-1 transition-all ${atLimit ? "bg-red-400/60" : "bg-signal/50"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              {/* Numeric input */}
              <input
                type="number"
                min={0}
                value={values[key] ?? 0}
                onChange={(e) => handleChange(key, e.target.value)}
                className="w-24 bg-white/5 border border-white/10 text-parchment text-xs font-mono px-2 py-1.5 focus:outline-none focus:border-white/25 transition-colors"
              />
            </div>
          );
        })}
      </div>

      {error && (
        <p className="text-red-400 text-xs font-mono">{error}</p>
      )}

      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-xs font-mono text-void bg-parchment px-4 py-2 hover:bg-parchment/80 disabled:opacity-40 transition-colors"
        >
          {saving ? <span className="animate-pulse">Saving…</span> : "Save counters"}
        </button>
        <button
          onClick={handleReset}
          disabled={saving}
          className="text-xs font-mono text-static border border-white/10 px-4 py-2 hover:text-parchment hover:border-white/20 disabled:opacity-40 transition-colors"
        >
          Reset to zero
        </button>
        {saved && (
          <span className="text-signal text-xs font-mono">✓ Saved</span>
        )}
      </div>

      <p className="text-static text-[10px] font-mono leading-relaxed pt-1 border-t border-white/8">
        Setting a counter below the weekly limit restores access. Set to the limit value to block
        further actions until the week resets. Admins bypass counters entirely.
      </p>
    </div>
  );
}
