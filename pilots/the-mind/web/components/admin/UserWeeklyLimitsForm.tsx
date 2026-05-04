"use client";

/**
 * UserWeeklyLimitsForm
 *
 * Inline admin control to override per-user weekly limits for persona
 * generation, probes, and chat. Null override = global default applies.
 *
 * Shows:
 *   - current effective limit (override badge if active)
 *   - numeric input to set a new limit
 *   - "Reset to global" button to clear the override (sends null)
 */

import { useState } from "react";

interface Props {
  userId: string;
  personaLimitOverride: number | null;
  probeLimitOverride:   number | null;
  chatLimitOverride:    number | null;
  globalLimits: {
    persona: number;
    probe:   number;
    chat:    number;
  };
}

interface FieldDef {
  label:       string;
  apiKey:      string;          // key sent to the backend set-limits endpoint
  override:    number | null;
  globalLimit: number;
}

export default function UserWeeklyLimitsForm({
  userId,
  personaLimitOverride,
  probeLimitOverride,
  chatLimitOverride,
  globalLimits,
}: Props) {
  const fields: FieldDef[] = [
    { label: "Personas / week",  apiKey: "persona_limit", override: personaLimitOverride, globalLimit: globalLimits.persona },
    { label: "Probes / week",    apiKey: "probe_limit",   override: probeLimitOverride,   globalLimit: globalLimits.probe   },
    { label: "Chats / week",     apiKey: "chat_limit",    override: chatLimitOverride,    globalLimit: globalLimits.chat    },
  ];

  // Draft values: start from override or global
  const [drafts, setDrafts] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      fields.map((f) => [f.apiKey, String(f.override ?? f.globalLimit)])
    )
  );

  const [saving,  setSaving]  = useState<string | null>(null); // apiKey currently saving
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [error,   setError]   = useState<string | null>(null);

  async function applyLimit(apiKey: string, value: number | null) {
    setSaving(apiKey);
    setSavedKey(null);
    setError(null);
    try {
      const res = await fetch(`/api/admin/users/${userId}/set-limits`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ [apiKey]: value }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? body.error ?? `Error ${res.status}`);
      }
      setSavedKey(apiKey);
      setTimeout(() => setSavedKey(null), 3000);
      // If resetting, update draft to reflect global
      if (value === null) {
        const f = fields.find((x) => x.apiKey === apiKey);
        if (f) setDrafts((d) => ({ ...d, [apiKey]: String(f.globalLimit) }));
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(null);
    }
  }

  function handleSet(apiKey: string) {
    const n = parseInt(drafts[apiKey] ?? "", 10);
    if (isNaN(n) || n < 0) { setError("Limit must be a non-negative integer"); return; }
    applyLimit(apiKey, n);
  }

  return (
    <div className="border border-white/8 bg-white/2 p-4 space-y-4">
      <p className="text-[10px] font-mono uppercase tracking-wider text-static">
        Weekly generation limits
      </p>

      <div className="space-y-4">
        {fields.map((f) => {
          const isOverridden = f.override !== null;
          const effective    = f.override ?? f.globalLimit;
          const isSaving     = saving === f.apiKey;
          const isSaved      = savedKey === f.apiKey;

          return (
            <div key={f.apiKey} className="space-y-1.5">
              {/* Label row */}
              <div className="flex items-center gap-2">
                <span className="text-parchment text-xs font-medium">{f.label}</span>
                {isOverridden ? (
                  <span className="text-[9px] font-mono px-1.5 py-0.5 bg-signal/15 text-signal border border-signal/25">
                    OVERRIDE: {effective}
                  </span>
                ) : (
                  <span className="text-[9px] font-mono text-static">
                    global: {f.globalLimit}
                  </span>
                )}
              </div>

              {/* Input + actions */}
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  value={drafts[f.apiKey] ?? ""}
                  onChange={(e) =>
                    setDrafts((d) => ({ ...d, [f.apiKey]: e.target.value }))
                  }
                  className="w-20 bg-white/5 border border-white/10 text-parchment text-xs font-mono px-2 py-1.5 focus:outline-none focus:border-white/25 transition-colors"
                  disabled={isSaving}
                />
                <button
                  onClick={() => handleSet(f.apiKey)}
                  disabled={isSaving}
                  className="text-xs font-mono text-void bg-parchment px-3 py-1.5 hover:bg-parchment/80 disabled:opacity-40 transition-colors"
                >
                  {isSaving ? <span className="animate-pulse">…</span> : "Set"}
                </button>
                {isOverridden && (
                  <button
                    onClick={() => applyLimit(f.apiKey, null)}
                    disabled={isSaving}
                    className="text-[10px] font-mono text-static hover:text-parchment disabled:opacity-40 transition-colors underline underline-offset-2"
                  >
                    Reset to global
                  </button>
                )}
                {isSaved && (
                  <span className="text-signal text-xs font-mono">✓</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <p className="text-red-400 text-[11px] font-mono">{error}</p>
      )}

      <p className="text-[10px] font-mono text-static/70 leading-relaxed border-t border-white/8 pt-3">
        Overrides are permanent until reset. "Reset to global" removes the
        override so the user reverts to the platform default.
        Admins bypass all limits regardless.
      </p>
    </div>
  );
}
