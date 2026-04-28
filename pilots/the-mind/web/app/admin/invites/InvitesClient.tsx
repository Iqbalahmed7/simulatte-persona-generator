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

type Tab = "bulk" | "email" | "bulkmany";

interface BulkResult {
  label: string | null;
  email: string | null;
  code?: string;
  url?: string;
  ok: boolean;
  error?: string;
  email_sent?: boolean;
  email_error?: string;
}

export default function InvitesClient({ initialCodes }: { initialCodes: InviteRow[] }) {
  const [codes, setCodes] = useState<InviteRow[]>(initialCodes);
  const [tab, setTab] = useState<Tab>("bulkmany");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Bulk-code form
  const [label, setLabel] = useState("");
  const [maxUses, setMaxUses] = useState("");

  // Email-invite form
  const [emailTo, setEmailTo] = useState("");
  const [emailNote, setEmailNote] = useState("");

  // Bulk-many form: one entry per line. Each line is either a name
  // (label-only) or an email (auto-detected if it has @) or
  // "Name <email>" / "Name, email" for both.
  const [bulkInput, setBulkInput] = useState("");
  const [bulkNote, setBulkNote] = useState("");
  const [bulkResults, setBulkResults] = useState<BulkResult[]>([]);

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

  // Parse the bulk textarea into items. One entry per line; supports:
  //   "Name"                    → label only
  //   "alice@x.com"             → email only (label derived)
  //   "Name <alice@x.com>"      → both
  //   "Name, alice@x.com"       → both
  function parseBulkLines(input: string): Array<{ label?: string; email?: string }> {
    return input
      .split(/\r?\n/)
      .map((raw) => raw.trim())
      .filter(Boolean)
      .map((line) => {
        // "Name <email>"
        const angle = line.match(/^(.*?)\s*<\s*([^>]+?)\s*>\s*$/);
        if (angle && angle[2].includes("@")) {
          return { label: angle[1].trim() || undefined, email: angle[2].trim().toLowerCase() };
        }
        // "Name, email" or "Name; email"
        const splitIdx = line.search(/[,;]\s*/);
        if (splitIdx > 0) {
          const left = line.slice(0, splitIdx).trim();
          const right = line.slice(splitIdx).replace(/^[,;]\s*/, "").trim();
          if (right.includes("@")) {
            return { label: left || undefined, email: right.toLowerCase() };
          }
        }
        // Just an email
        if (line.includes("@") && !line.includes(" ")) {
          return { email: line.toLowerCase() };
        }
        // Just a label
        return { label: line };
      });
  }

  async function onBulkMany(e: React.FormEvent) {
    e.preventDefault();
    const items = parseBulkLines(bulkInput);
    if (items.length === 0) {
      setErr("Add at least one name or email per line.");
      return;
    }
    setBusy(true);
    setErr(null);
    setBulkResults([]);
    try {
      const res = await fetch("/api/admin/invites/bulk", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ items, note: bulkNote.trim() || null }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(j.detail || `HTTP ${res.status}`);
      }
      setBulkResults(Array.isArray(j.results) ? j.results : []);
      setBulkInput("");
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function copyResultLink(url: string, code: string) {
    navigator.clipboard?.writeText(url);
    setCopied(code);
    setTimeout(() => setCopied(null), 1500);
  }

  function copyAllLinks() {
    const lines = bulkResults
      .filter((r) => r.ok && r.url)
      .map((r) => `${r.label ?? r.email ?? "—"}\t${r.url}`)
      .join("\n");
    navigator.clipboard?.writeText(lines);
    setCopied("__ALL__");
    setTimeout(() => setCopied(null), 1500);
  }

  function exportCsv() {
    const header = "label,email,code,url,ok,error\n";
    const rows = bulkResults.map((r) => {
      const cells = [r.label ?? "", r.email ?? "", r.code ?? "", r.url ?? "", r.ok ? "yes" : "no", r.error ?? ""];
      return cells.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",");
    }).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `invites-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
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
      <div className="flex gap-1 border-b border-parchment/10 flex-wrap">
        {(["bulkmany", "bulk", "email"] as Tab[]).map((t) => (
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
            {t === "bulkmany"
              ? "Bulk (many)"
              : t === "bulk"
              ? "One shareable code"
              : "Email a person"}
          </button>
        ))}
      </div>

      {tab === "bulkmany" && (
        <form onSubmit={onBulkMany} className="border border-parchment/10 p-6 space-y-4">
          <div>
            <p className="text-parchment/70 text-sm leading-relaxed">
              One entry per line. Each line becomes its own invite link.
              Adding an email auto-sends the invite; otherwise you get a labelled
              link to share manually (WhatsApp, Slack, etc.).
            </p>
            <p className="text-parchment/50 text-[11px] font-mono mt-2">
              Formats: <code>Name</code> · <code>email@x.com</code> ·{" "}
              <code>Name &lt;email@x.com&gt;</code> · <code>Name, email@x.com</code>
            </p>
          </div>
          <div>
            <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
              Recipients (max 100)
            </label>
            <textarea
              value={bulkInput}
              onChange={(e) => setBulkInput(e.target.value)}
              placeholder={"Alice from college\nBob <bob@a16z.com>\nRiya, riya@gmail.com"}
              rows={8}
              className="w-full bg-transparent border border-parchment/20 px-3 py-2 text-sm font-mono focus:border-signal focus:outline-none resize-y"
              style={{ minHeight: 160 }}
            />
            <p className="text-parchment/50 text-[10px] font-mono mt-1">
              {parseBulkLines(bulkInput).length} entr
              {parseBulkLines(bulkInput).length === 1 ? "y" : "ies"}
            </p>
          </div>
          <div>
            <label className="block text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
              Optional shared note (only used in emailed invites)
            </label>
            <textarea
              value={bulkNote}
              onChange={(e) => setBulkNote(e.target.value)}
              placeholder="Quick early access for trusted people. Try the persona builder."
              rows={2}
              className="w-full bg-transparent border border-parchment/20 px-3 py-2 text-sm focus:border-signal focus:outline-none resize-none"
            />
          </div>
          <button
            type="submit"
            disabled={busy || parseBulkLines(bulkInput).length === 0}
            className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-2 disabled:opacity-50"
          >
            {busy ? "Generating…" : `Generate ${parseBulkLines(bulkInput).length || ""} link${parseBulkLines(bulkInput).length === 1 ? "" : "s"}`}
          </button>
        </form>
      )}

      {bulkResults.length > 0 && (
        <div className="border border-signal/30 bg-signal/[0.04] p-5">
          <div className="flex items-baseline justify-between mb-3 flex-wrap gap-2">
            <p className="text-[11px] font-mono uppercase tracking-widest text-signal">
              Just minted · {bulkResults.filter((r) => r.ok).length} of {bulkResults.length}
            </p>
            <div className="flex gap-3">
              <button
                onClick={copyAllLinks}
                className="text-[10px] font-mono uppercase tracking-widest text-parchment/70 hover:text-signal"
              >
                {copied === "__ALL__" ? "Copied all" : "Copy all"}
              </button>
              <button
                onClick={exportCsv}
                className="text-[10px] font-mono uppercase tracking-widest text-parchment/70 hover:text-signal"
              >
                Export CSV
              </button>
            </div>
          </div>
          <div className="space-y-2">
            {bulkResults.map((r, i) => (
              <div
                key={i}
                className={
                  "flex items-center gap-3 py-2 border-b border-parchment/5 last:border-b-0 " +
                  (r.ok ? "" : "opacity-60")
                }
              >
                <div className="flex-1 min-w-0">
                  <div className="text-parchment text-sm truncate">
                    {r.label || r.email || "—"}
                  </div>
                  {r.ok ? (
                    <div className="font-mono text-[11px] text-parchment/55 truncate">
                      {r.url}
                      {r.email && (
                        <span className={r.email_sent === false ? "text-amber-400 ml-2" : "text-signal/70 ml-2"}>
                          {r.email_sent === false ? "· email failed" : "· emailed"}
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="font-mono text-[11px] text-amber-400">
                      {r.error || "failed"}
                    </div>
                  )}
                </div>
                {r.ok && r.url && r.code && (
                  <button
                    onClick={() => copyResultLink(r.url!, r.code!)}
                    className="text-[10px] font-mono uppercase tracking-widest text-parchment/60 hover:text-signal flex-shrink-0"
                  >
                    {copied === r.code ? "Copied" : "Copy"}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

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
