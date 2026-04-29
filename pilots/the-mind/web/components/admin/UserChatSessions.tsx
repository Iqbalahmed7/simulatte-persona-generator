"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

interface ChatSessionRow {
  session_id: string;
  persona_id: string;
  persona_name: string | null;
  started_at: string | null;
  last_message_at: string | null;
  message_count: number;
  flagged_count: number;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + "Z";
}

export default function UserChatSessions({ userId }: { userId: string }) {
  const [rows, setRows] = useState<ChatSessionRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`/api/admin/users/${userId}/chats`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => {
        if (!alive) return;
        setRows(Array.isArray(data) ? (data as ChatSessionRow[]) : []);
      })
      .catch((e) => {
        if (alive) setError(e.message ?? "Failed to load chat sessions");
      });
    return () => {
      alive = false;
    };
  }, [userId]);

  return (
    <section className="mb-10">
      <h2 className="text-[11px] font-mono uppercase tracking-widest text-parchment/50 mb-4">
        Chat sessions{rows ? ` (${rows.length})` : ""}
      </h2>

      {error && (
        <p className="font-mono text-[11px] text-static border border-parchment/10 px-3 py-2">
          {error}
        </p>
      )}

      {rows === null && !error && (
        <p className="text-parchment/40 text-sm">Loading…</p>
      )}

      {rows && rows.length === 0 && (
        <p className="text-parchment/40 text-sm py-2">No chat sessions yet.</p>
      )}

      {rows && rows.length > 0 && (
        <div className="border border-parchment/10">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left font-mono text-[10px] uppercase tracking-widest text-parchment/40">
                <th className="px-3 py-2 border-b border-parchment/10">Persona</th>
                <th className="px-3 py-2 border-b border-parchment/10">Started</th>
                <th className="px-3 py-2 border-b border-parchment/10">Last message</th>
                <th className="px-3 py-2 border-b border-parchment/10 text-right">Messages</th>
                <th className="px-3 py-2 border-b border-parchment/10 text-right">Flagged</th>
                <th className="px-3 py-2 border-b border-parchment/10 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.session_id} className="border-b border-parchment/5 last:border-b-0">
                  <td className="px-3 py-2 text-parchment">{r.persona_name ?? "Persona"}</td>
                  <td className="px-3 py-2 font-mono text-[11px] text-parchment/70">
                    {fmt(r.started_at)}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-parchment/70">
                    {fmt(r.last_message_at)}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-parchment/70 text-right">
                    {r.message_count}
                  </td>
                  <td
                    className={`px-3 py-2 font-mono text-[11px] text-right ${
                      r.flagged_count > 0 ? "text-amber-400" : "text-parchment/40"
                    }`}
                  >
                    {r.flagged_count}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      href={`/admin/chats/${r.session_id}`}
                      className="font-mono text-[11px] text-signal hover:underline"
                    >
                      open ↗
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
