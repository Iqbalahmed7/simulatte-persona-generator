"use client";

import { useState } from "react";

interface Row {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string | null;
  user_image: string | null;
  user_access_status: string;
  reason: string | null;
  status: string;
  created_at: string | null;
  resolved_at: string | null;
  resolved_by_email: string | null;
}

export default function AccessRequestsClient({ initialRows }: { initialRows: Row[] }) {
  const [rows, setRows] = useState<Row[]>(initialRows);
  const [busy, setBusy] = useState<string | null>(null);
  const [filter, setFilter] = useState<"pending" | "all">("pending");

  async function refresh() {
    const res = await fetch("/api/admin/access-requests", { cache: "no-store" });
    if (res.ok) setRows(await res.json());
  }

  async function approve(userId: string) {
    setBusy(userId);
    try {
      await fetch(`/api/admin/users/${userId}/approve`, { method: "POST" });
      await refresh();
    } finally {
      setBusy(null);
    }
  }

  async function dismiss(reqId: string) {
    if (!confirm("Dismiss this request? The user stays on the waitlist.")) return;
    setBusy(reqId);
    try {
      await fetch(`/api/admin/access-requests/${reqId}/dismiss`, { method: "POST" });
      await refresh();
    } finally {
      setBusy(null);
    }
  }

  const visible = filter === "pending" ? rows.filter((r) => r.status === "pending") : rows;

  return (
    <div className="space-y-6">
      <div className="flex gap-1 border-b border-parchment/10">
        {(["pending", "all"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={
              "px-4 py-2 text-[11px] font-mono uppercase tracking-widest transition-colors " +
              (filter === f
                ? "text-signal border-b-2 border-signal"
                : "text-parchment/60 hover:text-parchment")
            }
          >
            {f === "pending"
              ? `Pending (${rows.filter((r) => r.status === "pending").length})`
              : `All (${rows.length})`}
          </button>
        ))}
      </div>

      {visible.length === 0 && (
        <p className="text-parchment/40 text-sm py-8 text-center">
          No requests in this view.
        </p>
      )}

      <div className="space-y-3">
        {visible.map((r) => (
          <div key={r.id} className="border border-parchment/10 p-5">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div>
                <div className="font-condensed font-bold text-parchment text-lg">
                  {r.user_name ?? "(no name)"}
                </div>
                <a
                  href={`mailto:${r.user_email}`}
                  className="font-mono text-xs text-signal"
                >
                  {r.user_email}
                </a>
                <div className="font-mono text-[10px] text-parchment/40 mt-1 tracking-widest uppercase">
                  {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                  {r.status !== "pending" && (
                    <span className="ml-3">— {r.status}{r.resolved_by_email ? ` by ${r.resolved_by_email}` : ""}</span>
                  )}
                </div>
              </div>
              {r.status === "pending" && (
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => approve(r.user_id)}
                    disabled={busy === r.user_id}
                    className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-4 py-2 text-xs disabled:opacity-50"
                  >
                    {busy === r.user_id ? "Approving…" : "Approve"}
                  </button>
                  <button
                    onClick={() => dismiss(r.id)}
                    disabled={busy === r.id}
                    className="border border-parchment/20 text-parchment/72 hover:text-amber-400 hover:border-amber-400 font-condensed font-bold uppercase tracking-wider px-4 py-2 text-xs"
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
            {r.reason && (
              <blockquote className="border-l-2 border-parchment/20 pl-4 text-parchment/72 text-sm italic mt-3">
                {r.reason}
              </blockquote>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
