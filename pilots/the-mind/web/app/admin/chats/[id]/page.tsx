"use client";

import Link from "next/link";
import { useEffect, useState, use as usePromise } from "react";

interface Message {
  role: "user" | "persona";
  content: string;
  created_at: string | null;
  flagged: boolean;
}

interface ChatPayload {
  session: {
    session_id: string;
    user_id: string;
    user_email: string | null;
    persona_id: string;
    persona_name: string | null;
    started_at: string | null;
    last_message_at: string | null;
    message_count: number;
    flagged_count: number;
  };
  messages: Message[];
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + "Z";
}

export default function AdminChatViewerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = usePromise(params);
  const [data, setData] = useState<ChatPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`/api/admin/chats/${id}`, { cache: "no-store" })
      .then((r) =>
        r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
      )
      .then((j) => {
        if (alive) setData(j as ChatPayload);
      })
      .catch((e) => {
        if (alive) setError(e.message ?? "Failed to load chat");
      });
    return () => {
      alive = false;
    };
  }, [id]);

  if (error) {
    return (
      <div>
        <Link
          href="/admin/users"
          className="text-xs font-mono text-parchment/50 hover:text-signal"
        >
          ← Users
        </Link>
        <p className="font-mono text-[11px] text-static border border-parchment/10 px-3 py-2 mt-6">
          {error}
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <p className="text-parchment/40 text-sm">Loading…</p>
      </div>
    );
  }

  const { session, messages } = data;
  const personaName = session.persona_name ?? "Persona";

  return (
    <div>
      <Link
        href={`/admin/users/${session.user_id}`}
        className="text-xs font-mono text-parchment/50 hover:text-signal"
      >
        ← Back to user
      </Link>

      <div className="mt-4 mb-6 border border-parchment/10 p-5">
        <div className="flex items-baseline justify-between gap-4 mb-3">
          <h1 className="font-condensed font-bold text-parchment text-2xl">
            {personaName}
          </h1>
          <a
            href={`/api/admin/chats/${session.session_id}/download`}
            className="px-3 py-2 text-[11px] font-semibold tracking-widest uppercase text-void bg-signal hover:bg-signal/90"
          >
            Download
          </a>
        </div>
        <dl className="grid grid-cols-2 gap-y-1 text-[11px] font-mono text-parchment/70">
          <dt className="text-parchment/40">User</dt>
          <dd>{session.user_email ?? session.user_id}</dd>
          <dt className="text-parchment/40">Started</dt>
          <dd>{fmt(session.started_at)}</dd>
          <dt className="text-parchment/40">Last message</dt>
          <dd>{fmt(session.last_message_at)}</dd>
          <dt className="text-parchment/40">Messages</dt>
          <dd>{session.message_count}</dd>
          {session.flagged_count > 0 && (
            <>
              <dt className="text-amber-400/80">Flagged</dt>
              <dd className="text-amber-400">{session.flagged_count}</dd>
            </>
          )}
        </dl>
      </div>

      <div className="space-y-4">
        {messages.map((m, idx) => {
          const isUser = m.role === "user";
          const flaggedCls = m.flagged ? "border border-amber-400" : "";
          return (
            <div
              key={idx}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div className="max-w-[80%]">
                <div
                  className={`px-4 py-3 ${
                    isUser
                      ? "bg-parchment/5 text-parchment"
                      : "bg-signal/[0.08] text-parchment"
                  } ${flaggedCls}`}
                >
                  <p className="text-[10px] font-mono uppercase tracking-widest text-static mb-1">
                    {isUser ? "User" : personaName}
                  </p>
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">
                    {m.content}
                  </p>
                </div>
                <div className="flex items-center gap-3 mt-1 px-1">
                  <span className="font-mono text-[10px] text-static">
                    {fmt(m.created_at)}
                  </span>
                  {m.flagged && (
                    <span className="font-mono text-[10px] uppercase tracking-widest text-signal">
                      flagged
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        {messages.length === 0 && (
          <p className="text-parchment/40 text-sm text-center py-6">
            No messages.
          </p>
        )}
      </div>
    </div>
  );
}
