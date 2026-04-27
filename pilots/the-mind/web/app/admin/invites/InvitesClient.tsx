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
  created_by_user_id: string | null;
  sent_to_email: string | null;
  sent_at: string | null;
}

type Tab = "bulk" | "email";

export default function InvitesClient({ initialCodes }: { initialCodes: InviteRow[] }) {
  const [codes, setCodes] = useState<InviteRow[]>(initialCodes);
  const [tab, setTab] = useState<Tab>("bulk");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Bulk-code form
  const [label, setLabel] = useState("");
  const [maxUses, setMaxUses] = useState("");

  // Email-invite form
  const [emailTo, setEmailTo] = useState("");
  const [emailNote, setEmailNote] = useState("");

  async function refresh() {
    const res = await fetch("/api/admin/invites", { cache: "no-store" });
    if (res.ok) setCodes(await res.json());
  }

  async function onCreateBulk(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/admin/invites", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          label: label.trim() || null,
          max_uses: maxUses ? Number(maxUses) : null,
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${res.status}`);
      }
      setLabel("");
      setMaxUses("");
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onSendEmail(e: React.FormEvent) {
    e.preventDefault();
    if (!emailTo.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/admin/invites/email", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          to_email: emailTo.trim(),
          note: emailNote.trim() || null,
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${res.status}`);
      }
      setEmailTo("");
      setEmailNote("");
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onDeactivate(c: string) {
    if (!confirm(`Deactivate ${c}? No new redemptions will be accepted.`)) return;
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

  function kindLabel(c: InviteRow): string {
    if (c.created_by_user_id) return "personal";
    if (c.sent_to_email) return "emailed";
    return "admin";
  }

  return (
    <div className="space-y-8">
      {/* Tab switcher */}
      <div className="flex gap-1 border-b border-parchment/10">
        {(["bulk", "email"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={
              "px-4 py-2 text-[11px] font-mono uppercase tracking-widest transition-colors " +
              (tab === t
                ? "text-signal border-b-2 border-signal"
                : "text-parchment/60 hover:text-parchment")
            }
          >
            {t === "bulk" ? "Shareable code" : "Email a person"}
          </button>
        ))}
      </div>

      {tab === "bulk" && (
        <form onSubmit={onCreateBulk} className="border border-parchment/10 p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-3">
            <p className="text-parchment/60 text-sm">
              Mints a random URL-safe code. Use the label to track which channel
              it went to (e.g. &ldquo;LinkedIn post Apr 27&rdquo;).
            </p>
          </div>
          <div>
            <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
              Label
            </label>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="LinkedIn post Apr 27"
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
              disabled={busy}
              className="w-full bg-signal text-void font-condensed font-bold uppercase tracking-wider py-2 disabled:opacity-50"
            >
              {busy ? "Minting…" : "Mint code"}
            </button>
          </div>
        </form>
      )}

      {tab === "email" && (
        <form onSubmit={onSendEmail} className="border border-parchment/10 p-6 space-y-4">
          <p className="text-parchment/60 text-sm">
            Mints a one-use code and emails the invite link directly. Good for
            personal outreach.
          </p>
          <div>
            <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
              Send to email
            </label>
            <input
              type="email"
              value={emailTo}
              onChange={(e) => setEmailTo(e.target.value)}
              placeholder="sarah@somecompany.com"
              required
              className="w-full bg-transparent border border-parchment/20 px-3 py-2 text-sm focus:border-signal focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
              Optional note (shown in the email)
            </label>
            <textarea
              value={emailNote}
              onChange={(e) => setEmailNote(e.target.value)}
              placeholder="Hey Sarah, here's your access — try the persona builder for the Aug launch."
              rows={3}
              className="w-full bg-transparent border border-parchment/20 px-3 py-2 text-sm focus:border-signal focus:outline-none resize-none"
            />
          </div>
          <button
            type="submit"
            disabled={busy || !emailTo.trim()}
            className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-2 disabled:opacity-50"
          >
            {busy ? "Sending…" : "Mint + send invite"}
          </button>
        </form>
      )}

      {err && (
        <p className="text-amber-400 text-sm font-mono">{err}</p>
      )}

      <div>
        <h2 className="font-condensed font-bold text-xl uppercase tracking-wider mb-4">
          {codes.length} code{codes.length === 1 ? "" : "s"}
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] font-mono uppercase tracking-widest text-parchment/50 border-b border-parchment/10">
                <th className="py-3 pr-4">Code</th>
                <th className="py-3 pr-4">Kind</th>
                <th className="py-3 pr-4">Label / Sent to</th>
                <th className="py-3 pr-4">Used</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Created</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {codes.map((c) => (
                <tr key={c.code} className="border-b border-parchment/5">
                  <td className="py-3 pr-4 font-mono text-parchment">{c.code}</td>
                  <td className="py-3 pr-4 font-mono text-xs text-parchment/60">
                    {kindLabel(c)}
                  </td>
                  <td className="py-3 pr-4 text-parchment/72">
                    {c.sent_to_email ?? c.label ?? "—"}
                  </td>
                  <td className="py-3 pr-4 font-mono">
                    {c.actual_redemptions}
                    {c.max_uses != null && (
                      <span className="text-parchment/40"> / {c.max_uses}</span>
                    )}
                  </td>
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
                    No codes yet. Mint the first one above.
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
