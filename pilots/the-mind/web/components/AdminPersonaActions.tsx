/**
 * AdminPersonaActions — per-row Delete + Regenerate Portrait buttons
 * for the admin /admin/personas operator console.
 *
 * Both actions hit the API directly with the admin's session cookie
 * (Auth.js → backend HS256). Uses the /api/token bridge to get a Bearer
 * token rather than reaching for the cookie directly so the call works
 * even from edge contexts.
 */
"use client";

import { useState } from "react";
import { API } from "@/lib/api";

interface Props {
  personaId: string;
  /** Refresh the table after a successful delete. */
  onDeleted?: () => void;
}

export default function AdminPersonaActions({ personaId, onDeleted }: Props) {
  const [busy, setBusy] = useState<"none" | "delete" | "regen">("none");
  const [msg, setMsg] = useState<string>("");

  async function tokenHeader(): Promise<HeadersInit> {
    const r = await fetch("/api/token", { cache: "no-store" });
    if (!r.ok) throw new Error("auth");
    const { token } = await r.json();
    return { Authorization: `Bearer ${token}` };
  }

  async function onDelete() {
    if (!confirm(`Delete persona ${personaId}? This is irreversible.`)) return;
    setBusy("delete");
    setMsg("");
    try {
      const headers = await tokenHeader();
      const r = await fetch(`${API}/admin/generated/${personaId}`, {
        method: "DELETE", headers,
      });
      if (!r.ok) throw new Error(await r.text());
      setMsg("deleted");
      if (onDeleted) onDeleted();
      else if (typeof window !== "undefined") window.location.reload();
    } catch (e) {
      setMsg(`failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy("none");
    }
  }

  async function onRegen() {
    setBusy("regen");
    setMsg("regenerating…");
    try {
      const headers = await tokenHeader();
      const r = await fetch(`${API}/admin/generated/${personaId}/regenerate-portrait`, {
        method: "POST", headers,
      });
      if (!r.ok) throw new Error(await r.text());
      setMsg("done");
      if (typeof window !== "undefined") setTimeout(() => window.location.reload(), 800);
    } catch (e) {
      setMsg(`failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy("none");
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onRegen}
        disabled={busy !== "none"}
        className="text-[10px] font-mono uppercase tracking-widest px-2 py-1 border border-parchment/20 hover:border-signal/60 hover:text-signal disabled:opacity-40 disabled:cursor-wait"
      >
        {busy === "regen" ? "…" : "Regen"}
      </button>
      <button
        onClick={onDelete}
        disabled={busy !== "none"}
        className="text-[10px] font-mono uppercase tracking-widest px-2 py-1 border border-parchment/20 text-parchment/70 hover:border-red-500/60 hover:text-red-400 disabled:opacity-40 disabled:cursor-wait"
      >
        {busy === "delete" ? "…" : "Delete"}
      </button>
      {msg && (
        <span className="text-[10px] font-mono text-static lowercase">{msg}</span>
      )}
    </div>
  );
}
