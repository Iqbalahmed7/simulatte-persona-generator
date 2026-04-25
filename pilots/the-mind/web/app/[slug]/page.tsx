"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { chatWithPersona, fetchPersonas, PersonaCard, DecisionTrace } from "@/lib/api";

interface Message {
  role: "user" | "persona";
  text: string;
  trace?: DecisionTrace | null;
}

const SUGGESTED_QUESTIONS = [
  "Would you buy a protein powder for ₹500/month if it had clinical studies behind it?",
  "How do you decide whether a new wellness product is worth trying?",
  "What would make you switch from your current brand?",
  "How important is price vs quality when you shop for health products?",
  "What would you need to see before trusting a new supplement brand?",
];

function TracePanel({ trace, open, onToggle }: { trace: DecisionTrace; open: boolean; onToggle: () => void }) {
  return (
    <div className="mt-3 border-t border-parchment/10">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 pt-3 text-[11px] font-semibold tracking-widest uppercase text-static hover:text-parchment/50 transition-colors"
      >
        <span className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}>▶</span>
        Show reasoning
      </button>

      {open && (
        <div className="mt-4 space-y-4 text-sm">
          {/* Decision + confidence */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">Decision</p>
              <p className="text-parchment font-medium">{trace.decision}</p>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">Confidence</p>
              <p className="font-mono text-signal text-lg font-medium">{trace.confidence}</p>
            </div>
          </div>

          {/* Gut reaction */}
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">Gut reaction</p>
            <p className="text-parchment/80">{trace.gut_reaction}</p>
          </div>

          {/* Key drivers */}
          {trace.key_drivers.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-2">Key drivers</p>
              <ul className="space-y-1">
                {trace.key_drivers.map((d, i) => (
                  <li key={i} className="flex gap-2 text-parchment/75">
                    <span className="text-signal shrink-0">·</span>
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Objections */}
          {trace.objections.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-2">Objections</p>
              <ul className="space-y-1">
                {trace.objections.map((o, i) => (
                  <li key={i} className="flex gap-2 text-parchment/75">
                    <span className="text-static shrink-0">·</span>
                    {o}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* What would change mind */}
          {trace.what_would_change_mind && (
            <div>
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">What would change this</p>
              <p className="text-parchment/75">{trace.what_would_change_mind}</p>
            </div>
          )}

          {/* Follow-up action */}
          {trace.follow_up_action && (
            <div>
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">Follow-up action</p>
              <p className="text-parchment/75">{trace.follow_up_action}</p>
            </div>
          )}

          {/* Full reasoning trace */}
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-2">5-step reasoning</p>
            <pre className="text-[11px] font-mono text-parchment/60 whitespace-pre-wrap border border-parchment/8 p-3 leading-relaxed overflow-x-auto">
              {trace.reasoning_trace}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChatPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const [persona, setPersona] = useState<PersonaCard | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [openTraces, setOpenTraces] = useState<Record<number, boolean>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchPersonas()
      .then((ps) => setPersona(ps.find((p) => p.slug === slug) ?? null))
      .catch(() => setError("Could not load persona data"));
  }, [slug]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    setInput("");
    setError("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const res = await chatWithPersona(slug, text, true);
      setMessages((prev) => [
        ...prev,
        { role: "persona", text: res.reply, trace: res.decision_trace },
      ]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const toggleTrace = (idx: number) =>
    setOpenTraces((prev) => ({ ...prev, [idx]: !prev[idx] }));

  return (
    <div className="min-h-screen flex flex-col max-w-3xl mx-auto px-4 py-8">
      {/* Back nav */}
      <Link href="/" className="text-[11px] font-semibold tracking-widest uppercase text-static hover:text-parchment/50 transition-colors mb-8 inline-block">
        ← All personas
      </Link>

      {/* Persona header */}
      {persona && (
        <div className="border border-parchment/10 p-5 mb-8">
          <p className="text-[11px] font-semibold tracking-widest uppercase text-signal mb-1">
            {persona.life_stage.replace(/_/g, " ")}
          </p>
          <h1 className="font-condensed font-bold text-3xl text-parchment leading-none">
            {persona.name}
          </h1>
          <p className="text-static text-sm mt-1">
            {persona.age} · {persona.city}, {persona.country}
          </p>
          <p className="text-parchment/65 text-sm mt-2">{persona.description}</p>
          <div className="flex gap-3 mt-3">
            <span className="font-mono text-[10px] text-static">
              {persona.decision_style} decision style
            </span>
            <span className="text-parchment/20">·</span>
            <span className="font-mono text-[10px] text-static">
              consistency {persona.consistency_score}
            </span>
          </div>
        </div>
      )}

      {/* Suggested questions — shown when no messages yet */}
      {messages.length === 0 && !loading && (
        <div className="mb-6">
          <p className="text-[11px] font-semibold tracking-widest uppercase text-static mb-3">
            Suggested questions
          </p>
          <div className="space-y-2">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="block w-full text-left border border-parchment/10 px-4 py-3 text-sm text-parchment/70 hover:text-parchment hover:border-parchment/25 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message thread */}
      <div className="flex-1 space-y-6 mb-6">
        {messages.map((msg, idx) => (
          <div key={idx}>
            {msg.role === "user" ? (
              <div className="flex justify-end">
                <div className="max-w-lg border border-parchment/15 px-4 py-3 text-sm text-parchment/85">
                  {msg.text}
                </div>
              </div>
            ) : (
              <div className="border-l-2 border-signal pl-4">
                <p className="text-[10px] font-mono text-static mb-2 uppercase tracking-widest">
                  {persona?.name.split(" ")[0] ?? slug}
                </p>
                <p className="text-parchment text-sm leading-relaxed">{msg.text}</p>
                {msg.trace && (
                  <TracePanel
                    trace={msg.trace}
                    open={!!openTraces[idx]}
                    onToggle={() => toggleTrace(idx)}
                  />
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="border-l-2 border-signal/40 pl-4">
            <p className="text-[10px] font-mono text-static mb-2 uppercase tracking-widest">
              {persona?.name.split(" ")[0] ?? slug}
            </p>
            <div className="flex gap-1 items-center h-5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="inline-block w-1 h-1 bg-signal/60 rounded-full animate-pulse"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {error && (
          <p className="font-mono text-[11px] text-static border border-parchment/10 px-3 py-2">
            {error}
          </p>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border border-parchment/15 flex">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
          placeholder={`Ask ${persona?.name.split(" ")[0] ?? "this persona"} anything…`}
          disabled={loading}
          className="flex-1 bg-transparent px-4 py-3 text-sm text-parchment placeholder:text-static/50 outline-none disabled:opacity-50"
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="px-4 py-3 text-[11px] font-semibold tracking-widest uppercase text-void bg-signal hover:bg-signal/90 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </div>
  );
}
