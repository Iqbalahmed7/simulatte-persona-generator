/**
 * RegenerateAllPortraits — admin header button + status poller.
 *
 * Kicks off the bulk fal.ai re-roll, then polls the status endpoint
 * every 4s while running. Lets the operator refresh existing portraits
 * to pick up the topical-prompt rebuild without nuking the wall.
 */
"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";

interface Status { running: boolean; done: number; total: number; errors: string[]; }

export default function RegenerateAllPortraits() {
  const [s, setS] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);

  async function tokenHeader(): Promise<HeadersInit> {
    const r = await fetch("/api/token", { cache: "no-store" });
    if (!r.ok) throw new Error("auth");
    const { token } = await r.json();
    return { Authorization: `Bearer ${token}` };
  }

  async function fetchStatus() {
    try {
      const headers = await tokenHeader();
      const r = await fetch(`${API}/admin/regenerate-all-portraits/status`, { headers, cache: "no-store" });
      if (r.ok) setS(await r.json());
    } catch { /* swallow */ }
  }

  useEffect(() => { void fetchStatus(); }, []);

  // Poll while a run is active.
  useEffect(() => {
    if (!s?.running) return;
    const id = setInterval(fetchStatus, 4000);
    return () => clearInterval(id);
  }, [s?.running]);

  async function start() {
    if (!confirm("Re-roll EVERY existing portrait? This will spend fal.ai credits (~$0.05/image)."))
      return;
    setBusy(true);
    try {
      const headers = await tokenHeader();
      await fetch(`${API}/admin/regenerate-all-portraits`, { method: "POST", headers });
      void fetchStatus();
    } finally { setBusy(false); }
  }

  const running = s?.running ?? false;
  const label = running
    ? `Regenerating ${s?.done ?? 0}/${s?.total ?? 0}…`
    : "Regenerate all portraits";

  return (
    <div className="flex items-center gap-3">
      {s && !running && s.errors?.length > 0 && (
        <span className="text-[10px] font-mono text-red-400/70">{s.errors.length} failed</span>
      )}
      <button
        onClick={start}
        disabled={busy || running}
        className="text-[11px] font-mono uppercase tracking-widest px-3 py-2 border border-signal/40 text-signal hover:bg-signal hover:text-void disabled:opacity-50 disabled:cursor-wait"
      >
        {label}
      </button>
    </div>
  );
}
