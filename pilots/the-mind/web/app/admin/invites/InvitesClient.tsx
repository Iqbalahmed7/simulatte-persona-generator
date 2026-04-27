"use client";

import { useState } from "react";

interface InviteRow {
  code: string;
  label: string | null;
  max_uses: number | null;
  used_count: number;
  actual_redemptions: number;
  active: boolean;
  created_at: string | null;
  created_by_email: string | null;
}

export default function InvitesClient({ initialCodes }: { initialCodes: InviteRow[] }) {
  const [codes, setCodes] = useState<InviteRow[]>(initialCodes);
  const [code, setCode] = useState("");
  const [label, setLabel] = useState("");
  const [maxUses, setMaxUses] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  async function refresh() {
    const res = await fetch("/api/admin/invites", { cache: "no-store" });
    if (res.ok) setCodes(await res.json());
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/admin/invites", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          code: code.trim().toUpperCase(),
          label: label.trim() || null,
          max_uses: maxUses ? Number(maxUses) : null,
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${res.status}`);
      }
      setCode("");
      setLabel("");
      setMaxUses("");
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onDeactivate(c: string) {
    if (!confirm(`Deactivate ${c}? No new sign-ups will be accepted.`)) return;
    await fetch(`/api/admin/invites/${encodeURIComponent(c)}/deactivate`, { method: "POST" });
    await refresh();
  }

  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://mind.simulatte.io";

  function copyLink(c: string) {
    const link = `${origin}/invite/${encodeURIComponent(c)}`;
    navigator.clipboard?.writeText(link);
    setCopied(c);
    setTimeout(() => setCopied(null), 1500);
  }

  return (
    <div className="space-y-10">
      <form onSubmit={onCreate} className="border border-parchment/10 p-6 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
            Code
          </label>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="EARLYACCESS"
            className="w-full bg-transparent border border-parchment/20 px-3 py-2 font-mono text-sm focus:border-signal focus:outline-none"
            required
          />
        </div>
        <div>
          <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
            Label
          </label>
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Twitter post Apr 27"
            className="w-full bg-transparent border border-parchment/20 px-3 py-2 text-sm focus:border-signal focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
            Max uses (blank = unlimited)
          </label>
          <input
            type="number"
            min={1}
            value={maxUses}
            onChange={(e) => setMaxUses(e.target.value)}
            placeholder="∞"
            className="w-full bg-transparent border border-parchment/20 px-3 py-2 font-mono text-sm focus:border-signal focus:outline-none"
          />
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={busy || !code.trim()}
            className="w-full bg-signal text-void font-condensed font-bold uppercase tracking-wider py-2 disabled:opacity-50"
          >
            {busy ? "Creating…" : "Create / Update"}
          </button>
        </div>
        {err && (
          <p className="md:col-span-4 text-amber-400 text-sm font-mono">{err}</p>
        )}
      </form>

      <div>
        <h2 className="font-condensed font-bold text-xl uppercase tracking-wider mb-4">
          {codes.length} code{codes.length === 1 ? "" : "s"}
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] font-mono uppercase tracking-widest text-parchment/50 border-b border-parchment/10">
                <th className="py-3 pr-4">Code</th>
                <th className="py-3 pr-4">Label</th>
                <th className="py-3 pr-4">Used</th>
                <th className="py-3 pr-4">Redeemed</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Created</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {codes.map((c) => (
                <tr key={c.code} className="border-b border-parchment/5">
                  <td className="py-3 pr-4 font-mono text-parchment">{c.code}</td>
                  <td className="py-3 pr-4 text-parchment/72">{c.label ?? "—"}</td>
                  <td className="py-3 pr-4 font-mono">
                    {c.used_count}
                    {c.max_uses != null && (
                      <span className="text-parchment/40"> / {c.max_uses}</span>
                    )}
                  </td>
                  <td className="py-3 pr-4 font-mono">{c.actual_redemptions}</td>
                  <td className="py-3 pr-4">
                    {c.active ? (
                      <span className="text-signal font-mono text-xs">ACTIVE</span>
                    ) : (
                      <span className="text-parchment/40 font-mono text-xs">INACTIVE</span>
                    )}
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs text-parchment/50">
                    {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="py-3 pr-4 text-right">
                    <button
                      onClick={() => copyLink(c.code)}
                      className="text-xs font-mono uppercase text-parchment/60 hover:text-signal mr-3"
                    >
                      {copied === c.code ? "Copied" : "Copy link"}
                    </button>
                    {c.active && (
                      <button
                        onClick={() => onDeactivate(c.code)}
                        className="text-xs font-mono uppercase text-parchment/60 hover:text-amber-400"
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {codes.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-parchment/40">
                    No codes yet. Create the first one above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
