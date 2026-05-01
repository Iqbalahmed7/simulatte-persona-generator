"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getTwin,
  startProbeSession,
  endProbeSession,
  streamProbeMessage,
  type TwinDetail,
  type ProbeSession,
  type ProbeSSEEvent,
  OperatorAllowanceError,
  OPERATOR_ERROR_MESSAGES,
} from "@/lib/operator-api";
import { useOperatorAllowance } from "@/components/OperatorAllowanceProvider";

// ── Types ──────────────────────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: "user" | "twin";
  content: string;
  operatorNote: string | null;
  streaming?: boolean;
}

interface OperatorNote {
  id: string;
  twinMessage: string;
  note: string;
  turnIndex: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function chevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function sendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M14 2L2 7l5 1.5L14 2zm0 0L9 14l-2-5.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function closeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="flex-1 flex flex-col gap-3 p-6 animate-pulse">
      {[...Array(4)].map((_, i) => (
        <div key={i} className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}>
          <div
            className="rounded-none bg-white/5"
            style={{
              height: 48,
              width: `${40 + Math.random() * 30}%`,
            }}
          />
        </div>
      ))}
    </div>
  );
}

function SessionEndedBanner({ onNewSession }: { onNewSession: () => void }) {
  return (
    <div className="mx-4 mb-3 border border-amber-500/30 bg-amber-500/5 px-4 py-3 flex items-center justify-between gap-4">
      <span className="text-amber-400 text-sm font-mono">
        Session ended — idle timeout (30 min). Start a new session to continue.
      </span>
      <button
        onClick={onNewSession}
        className="shrink-0 text-xs font-mono text-parchment border border-white/10 px-3 py-1.5 hover:bg-white/5 transition-colors"
      >
        New session
      </button>
    </div>
  );
}

function EndSessionModal({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-void border border-white/10 p-6 w-full max-w-sm">
        <h3 className="text-parchment font-mono text-sm font-semibold mb-2">
          End probe session?
        </h3>
        <p className="text-static text-sm mb-5">
          The session transcript will be preserved. You can start a new session from the Twin profile.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="text-static text-sm font-mono border border-white/10 px-4 py-2 hover:bg-white/5 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="text-parchment text-sm font-mono border border-red-500/40 bg-red-500/10 px-4 py-2 hover:bg-red-500/20 transition-colors"
          >
            End session
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function ProbePage() {
  const params = useParams<{ twin_id: string }>();
  const twinId = params.twin_id;
  const router = useRouter();
  const { handleOperatorAllowanceError } = useOperatorAllowance();

  // Data state
  const [twin, setTwin] = useState<TwinDetail | null>(null);
  const [session, setSession] = useState<ProbeSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [notes, setNotes] = useState<OperatorNote[]>([]);

  // UI state
  const [pageLoading, setPageLoading] = useState(true);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [showEndModal, setShowEndModal] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Input
  const [draft, setDraft] = useState("");
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const turnIndexRef = useRef(0);

  // ── Load twin ────────────────────────────────────────────────────────────

  useEffect(() => {
    getTwin(twinId)
      .then((t) => setTwin(t))
      .catch(() => setError("Failed to load Twin."))
      .finally(() => setPageLoading(false));
  }, [twinId]);

  // ── Start session on mount (after twin loads) ────────────────────────────

  const startSession = useCallback(async () => {
    setSessionLoading(true);
    setSessionEnded(false);
    setError(null);
    try {
      const s = await startProbeSession(twinId);
      setSession(s);
    } catch (err) {
      if (err instanceof OperatorAllowanceError) {
        handleOperatorAllowanceError(err, "start probe session");
      } else {
        setError((err as Error).message ?? "Failed to start session.");
      }
    } finally {
      setSessionLoading(false);
    }
  }, [twinId, handleOperatorAllowanceError]);

  useEffect(() => {
    if (!pageLoading && twin) {
      startSession();
    }
  }, [pageLoading, twin]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-scroll ──────────────────────────────────────────────────────────

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Auto-resize textarea ─────────────────────────────────────────────────

  function handleDraftChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setDraft(e.target.value);
    const el = composerRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }
  }

  // ── Send message ─────────────────────────────────────────────────────────

  async function handleSend() {
    const text = draft.trim();
    if (!text || !session || sending || sessionEnded) return;

    setDraft("");
    if (composerRef.current) composerRef.current.style.height = "auto";
    setSending(true);

    const userMsgId = uid();
    const twinMsgId = uid();
    const myTurn = ++turnIndexRef.current;

    // Optimistically add user message
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: text, operatorNote: null },
    ]);

    // Add streaming placeholder for twin
    setMessages((prev) => [
      ...prev,
      { id: twinMsgId, role: "twin", content: "", operatorNote: null, streaming: true },
    ]);

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    let noteBuffer = "";

    try {
      await streamProbeMessage(
        twinId,
        session.session_id,
        text,
        (evt: ProbeSSEEvent) => {
          if (evt.type === "token" && evt.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === twinMsgId
                  ? { ...m, content: m.content + evt.content }
                  : m
              )
            );
          } else if (evt.type === "operator_note" && evt.note) {
            noteBuffer = evt.note;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === twinMsgId ? { ...m, operatorNote: evt.note ?? null } : m
              )
            );
          } else if (evt.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === twinMsgId ? { ...m, streaming: false } : m
              )
            );
            if (noteBuffer) {
              setNotes((prev) => [
                {
                  id: uid(),
                  twinMessage:
                    prev.find((n) => n.turnIndex === myTurn - 1)?.twinMessage ?? text,
                  note: noteBuffer,
                  turnIndex: myTurn,
                },
                ...prev,
              ]);
              noteBuffer = "";
            }
          } else if (evt.type === "error") {
            const code = evt.error_code ?? "";
            if (code === "session_ended") {
              setSessionEnded(true);
              setMessages((prev) => prev.filter((m) => m.id !== twinMsgId));
            } else {
              const msg =
                OPERATOR_ERROR_MESSAGES[code] ??
                evt.error ??
                "Something went wrong.";
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === twinMsgId
                    ? { ...m, content: `⚠ ${msg}`, streaming: false }
                    : m
                )
              );
            }
          }
        },
        abortRef.current.signal
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        // cancelled
      } else if (err instanceof OperatorAllowanceError) {
        setMessages((prev) => prev.filter((m) => m.id !== twinMsgId));
        handleOperatorAllowanceError(err, "send probe message");
      } else {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === twinMsgId
              ? { ...m, content: `⚠ ${(err as Error).message}`, streaming: false }
              : m
          )
        );
      }
    } finally {
      setSending(false);
      composerRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  }

  // ── End session ───────────────────────────────────────────────────────────

  async function confirmEndSession() {
    if (!session) return;
    setEnding(true);
    try {
      await endProbeSession(twinId, session.session_id);
    } catch {
      // best-effort
    } finally {
      setShowEndModal(false);
      setEnding(false);
      router.push(`/operator/${twinId}`);
    }
  }

  // ── New session ───────────────────────────────────────────────────────────

  async function handleNewSession() {
    setMessages([]);
    setNotes([]);
    turnIndexRef.current = 0;
    await startSession();
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (pageLoading) {
    return (
      <div className="flex h-full">
        <div className="flex-1 flex flex-col">
          <LoadingSkeleton />
        </div>
      </div>
    );
  }

  if (error && !twin) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-static text-sm">{error}</p>
          <Link href="/operator" className="text-parchment text-sm underline">
            ← Back to Twins
          </Link>
        </div>
      </div>
    );
  }

  const twinName = twin?.full_name ?? "Twin";
  const canSend = !!session && !sending && !sessionEnded && !!draft.trim();

  return (
    <>
      {showEndModal && (
        <EndSessionModal
          onConfirm={confirmEndSession}
          onCancel={() => setShowEndModal(false)}
        />
      )}

      <div className="flex flex-col h-full overflow-hidden">
        {/* ── Header ────────────────────────────────────────────────────── */}
        <div className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-white/8">
          <div className="flex items-center gap-3">
            <Link
              href={`/operator/${twinId}`}
              className="text-static hover:text-parchment transition-colors"
            >
              {chevronLeft()}
            </Link>
            <div>
              <span className="text-parchment text-sm font-semibold">{twinName}</span>
              <span className="text-static text-xs font-mono ml-2">/ Probe</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {session && (
              <span className="text-static text-xs font-mono">
                {messages.filter((m) => m.role === "twin").length} exchange
                {messages.filter((m) => m.role === "twin").length !== 1 ? "s" : ""}
              </span>
            )}
            {session && !sessionEnded && (
              <button
                onClick={() => setShowEndModal(true)}
                disabled={ending}
                className="text-xs font-mono text-static border border-white/10 px-3 py-1.5 hover:text-parchment hover:border-white/20 transition-colors disabled:opacity-40"
              >
                End session
              </button>
            )}
          </div>
        </div>

        {/* ── Body ──────────────────────────────────────────────────────── */}
        <div className="flex-1 flex overflow-hidden">
          {/* LEFT — chat */}
          <div className="flex flex-col" style={{ width: "60%" }}>
            {/* Transcript */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {sessionLoading && (
                <div className="flex justify-center py-8">
                  <span className="text-static text-xs font-mono animate-pulse">
                    Connecting to {twinName}…
                  </span>
                </div>
              )}

              {!sessionLoading && messages.length === 0 && session && (
                <div className="flex justify-center py-8">
                  <span className="text-static text-xs font-mono">
                    Session open — send a message to begin
                  </span>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[75%] ${
                      msg.role === "user"
                        ? "bg-signal/10 border border-signal/20 text-signal"
                        : "bg-white/4 border border-white/8 text-parchment"
                    } px-4 py-3`}
                  >
                    {msg.role === "twin" && (
                      <p className="text-static text-[10px] font-mono uppercase tracking-wider mb-1.5">
                        {twinName}
                      </p>
                    )}
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                      {msg.streaming && (
                        <span className="inline-block w-1.5 h-4 bg-parchment/60 ml-0.5 animate-pulse align-middle" />
                      )}
                    </p>
                  </div>
                </div>
              ))}

              <div ref={bottomRef} />
            </div>

            {/* Session ended banner */}
            {sessionEnded && <SessionEndedBanner onNewSession={handleNewSession} />}

            {/* Composer */}
            {!sessionEnded && (
              <div className="shrink-0 border-t border-white/8 px-4 py-3">
                <div className="flex gap-3 items-end">
                  <textarea
                    ref={composerRef}
                    value={draft}
                    onChange={handleDraftChange}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      session
                        ? `Message ${twinName}… (⌘↵ to send)`
                        : "Starting session…"
                    }
                    disabled={!session || sending || sessionEnded}
                    rows={1}
                    className="flex-1 resize-none bg-white/4 border border-white/10 text-parchment text-sm placeholder:text-static/50 px-3 py-2.5 focus:outline-none focus:border-white/20 disabled:opacity-40 transition-colors"
                    style={{ minHeight: 42, maxHeight: 160 }}
                  />
                  <button
                    onClick={handleSend}
                    disabled={!canSend}
                    className="shrink-0 flex items-center justify-center w-10 h-10 border border-signal/30 bg-signal/8 text-signal hover:bg-signal/15 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    title="Send (⌘↵)"
                  >
                    {sendIcon()}
                  </button>
                </div>
                <p className="mt-1.5 text-static text-[10px] font-mono">
                  This is a simulation. Responses are AI-generated and do not represent the real individual.
                </p>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="w-px bg-white/8 shrink-0" />

          {/* RIGHT — Operator notes */}
          <div className="flex flex-col overflow-hidden" style={{ width: "40%" }}>
            <div className="shrink-0 px-5 py-3 border-b border-white/8">
              <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                Operator Notes
              </p>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
              {notes.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-12">
                  <div className="w-8 h-8 border border-white/10 mb-3 flex items-center justify-center">
                    <div className="w-3 h-3 border border-static/40" />
                  </div>
                  <p className="text-static text-xs font-mono leading-relaxed">
                    Operator notes appear here
                    <br />
                    after each Twin reply
                  </p>
                </div>
              ) : (
                notes.map((note) => (
                  <div
                    key={note.id}
                    className="border border-white/8 bg-white/2 px-4 py-3 space-y-2"
                  >
                    <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                      Turn {note.turnIndex}
                    </p>
                    <p className="text-parchment text-sm leading-relaxed">
                      {note.note}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
