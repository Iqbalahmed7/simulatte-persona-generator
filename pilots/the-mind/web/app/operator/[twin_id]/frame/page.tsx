"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getTwin,
  frameScore,
  type TwinDetail,
  type FrameScoreResponse,
  type FrameAnnotation,
  OperatorAllowanceError,
} from "@/lib/operator-api";
import { useOperatorAllowance } from "@/components/OperatorAllowanceProvider";

// ── Score colours ──────────────────────────────────────────────────────────

function scoreColor(s: number) {
  if (s >= 70) return "#A8FF3E"; // signal
  if (s >= 40) return "#E9E6DF"; // parchment
  return "#9A9997";              // static
}

function replyColor(r: "high" | "medium" | "low") {
  if (r === "high") return "text-signal border-signal/30 bg-signal/8";
  if (r === "medium") return "text-parchment border-white/20 bg-white/4";
  return "text-static border-white/10 bg-white/2";
}

function annotationColor(score: number) {
  if (score >= 70) return { bg: "bg-signal/15", border: "border-signal/30", dot: "bg-signal" };
  if (score >= 40) return { bg: "bg-white/8", border: "border-white/20", dot: "bg-parchment/60" };
  return { bg: "bg-red-500/10", border: "border-red-500/25", dot: "bg-red-400" };
}

// ── SVG score ring ─────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const r = 44;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = scoreColor(score);

  return (
    <div className="relative flex items-center justify-center" style={{ width: 108, height: 108 }}>
      <svg width="108" height="108" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="54" cy="54" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
        <circle
          cx="54" cy="54" r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={`${fill} ${circ}`}
          strokeLinecap="butt"
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono font-semibold text-2xl" style={{ color }}>
          {score}
        </span>
        <span className="text-static text-[9px] font-mono uppercase tracking-wider">/100</span>
      </div>
    </div>
  );
}

// ── Annotated draft view ───────────────────────────────────────────────────

function AnnotatedDraft({
  text,
  annotations,
  activeIdx,
  onHover,
}: {
  text: string;
  annotations: FrameAnnotation[];
  activeIdx: number | null;
  onHover: (i: number | null) => void;
}) {
  // Build non-overlapping segments sorted by start
  const sorted = [...annotations]
    .filter((a) => a.start >= 0 && a.end <= text.length && a.start < a.end)
    .sort((a, b) => a.start - b.start);

  const parts: Array<{ text: string; annIdx: number | null }> = [];
  let cursor = 0;

  for (const ann of sorted) {
    const idx = annotations.indexOf(ann);
    if (ann.start > cursor) {
      parts.push({ text: text.slice(cursor, ann.start), annIdx: null });
    }
    parts.push({ text: text.slice(ann.start, ann.end), annIdx: idx });
    cursor = ann.end;
  }
  if (cursor < text.length) {
    parts.push({ text: text.slice(cursor), annIdx: null });
  }

  return (
    <p className="text-parchment text-sm leading-relaxed whitespace-pre-wrap font-mono">
      {parts.map((part, i) => {
        if (part.annIdx === null) {
          return <span key={i}>{part.text}</span>;
        }
        const ann = annotations[part.annIdx];
        const { bg, border } = annotationColor(ann.score);
        const isActive = activeIdx === part.annIdx;
        return (
          <span
            key={i}
            className={`cursor-default border-b-2 transition-colors ${bg} ${border} ${
              isActive ? "ring-1 ring-white/20" : ""
            }`}
            onMouseEnter={() => onHover(part.annIdx)}
            onMouseLeave={() => onHover(null)}
          >
            {part.text}
          </span>
        );
      })}
    </p>
  );
}

// ── Annotation tooltip card ────────────────────────────────────────────────

function AnnotationCard({
  ann,
  index,
  active,
  onHover,
}: {
  ann: FrameAnnotation;
  index: number;
  active: boolean;
  onHover: (i: number | null) => void;
}) {
  const { dot } = annotationColor(ann.score);
  return (
    <div
      className={`border px-3 py-2.5 cursor-default transition-colors ${
        active ? "border-white/20 bg-white/5" : "border-white/8 bg-white/2"
      }`}
      onMouseEnter={() => onHover(index)}
      onMouseLeave={() => onHover(null)}
    >
      <div className="flex items-start gap-2">
        <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${dot}`} />
        <div className="flex-1 min-w-0 space-y-0.5">
          <p className="text-parchment text-xs font-mono leading-snug line-clamp-2">
            "{ann.segment}"
          </p>
          <p className="text-static text-[10px] leading-snug">{ann.reads_as}</p>
          {ann.risk && (
            <p className="text-red-400/80 text-[10px] leading-snug">⚠ {ann.risk}</p>
          )}
        </div>
        <span className="shrink-0 text-[10px] font-mono ml-1" style={{ color: scoreColor(ann.score) }}>
          {ann.score}
        </span>
      </div>
    </div>
  );
}

// ── Chevron icon ───────────────────────────────────────────────────────────

function chevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function lightningIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M7 1L2 7h4l-1 4 5-6H6l1-4z" fill="currentColor" />
    </svg>
  );
}

// ── History item ───────────────────────────────────────────────────────────

function HistoryItem({
  result,
  active,
  onClick,
}: {
  result: FrameScoreResponse;
  active: boolean;
  onClick: () => void;
}) {
  const color = scoreColor(result.overall_score);
  return (
    <button
      onClick={onClick}
      className={`w-full text-left border px-3 py-2 flex items-center gap-3 transition-colors ${
        active ? "border-white/20 bg-white/5" : "border-white/8 hover:bg-white/3"
      }`}
    >
      <span className="font-mono font-semibold text-sm" style={{ color }}>
        {result.overall_score}
      </span>
      <span className={`text-[10px] font-mono px-1.5 py-0.5 border ${replyColor(result.reply_probability)}`}>
        {result.reply_probability}
      </span>
      <span className="flex-1 text-static text-[10px] font-mono truncate">
        {new Date(result.scored_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </span>
    </button>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function FramePage() {
  const params = useParams<{ twin_id: string }>();
  const twinId = params.twin_id;
  const { handleOperatorAllowanceError } = useOperatorAllowance();

  const [twin, setTwin] = useState<TwinDetail | null>(null);
  const [pageLoading, setPageLoading] = useState(true);

  const [draft, setDraft] = useState("");
  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Results
  const [results, setResults] = useState<FrameScoreResponse[]>([]);
  const [activeResultIdx, setActiveResultIdx] = useState<number | null>(null);
  const activeResult = activeResultIdx !== null ? results[activeResultIdx] : null;

  // Annotation hover state
  const [hoverAnnIdx, setHoverAnnIdx] = useState<number | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load twin
  useEffect(() => {
    getTwin(twinId)
      .then(setTwin)
      .catch(() => setError("Failed to load Twin."))
      .finally(() => setPageLoading(false));
  }, [twinId]);

  // Auto-resize textarea
  function handleDraftChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setDraft(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 320)}px`;
    }
  }

  // Score
  async function handleScore() {
    const text = draft.trim();
    if (!text || scoring) return;
    setScoring(true);
    setError(null);
    try {
      const result = await frameScore(twinId, text);
      setResults((prev) => [result, ...prev]);
      setActiveResultIdx(0);
    } catch (err) {
      if (err instanceof OperatorAllowanceError) {
        handleOperatorAllowanceError(err, "score frame");
      } else {
        setError((err as Error).message ?? "Scoring failed.");
      }
    } finally {
      setScoring(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleScore();
    }
  }

  function selectResult(i: number) {
    setActiveResultIdx(i);
    setHoverAnnIdx(null);
  }

  // ── Render ──────────────────────────────────────────────────────────────

  const twinName = twin?.full_name ?? "Twin";

  if (pageLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-static text-xs font-mono animate-pulse">Loading…</span>
      </div>
    );
  }

  if (error && !twin) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-static text-sm">{error}</p>
          <Link href="/operator" className="text-parchment text-sm underline">← Back to Twins</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Header ────────────────────────────────────────────────────── */}
      <div className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-white/8">
        <div className="flex items-center gap-3">
          <Link href={`/operator/${twinId}`} className="text-static hover:text-parchment transition-colors">
            {chevronLeft()}
          </Link>
          <div>
            <span className="text-parchment text-sm font-semibold">{twinName}</span>
            <span className="text-static text-xs font-mono ml-2">/ Frame Score</span>
          </div>
        </div>
        {results.length > 0 && (
          <span className="text-static text-xs font-mono">
            {results.length} score{results.length !== 1 ? "s" : ""} this session
          </span>
        )}
      </div>

      {/* ── Body ──────────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT — composer + annotated view */}
        <div className="flex flex-col overflow-hidden" style={{ width: "55%" }}>
          {/* Composer */}
          <div className="shrink-0 border-b border-white/8 px-5 py-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                Draft message / email
              </p>
              <p className="text-static text-[10px] font-mono">{draft.length} chars</p>
            </div>
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={handleDraftChange}
              onKeyDown={handleKeyDown}
              placeholder={`Paste or type your outreach message to ${twinName}… (⌘↵ to score)`}
              rows={6}
              className="w-full resize-none bg-white/4 border border-white/10 text-parchment text-sm placeholder:text-static/50 px-3 py-2.5 focus:outline-none focus:border-white/20 transition-colors font-mono"
              style={{ minHeight: 120, maxHeight: 320 }}
            />
            <div className="flex items-center justify-between">
              <p className="text-static text-[10px] font-mono">
                Scored against {twinName}&#39;s decision architecture &amp; trigger map
              </p>
              <button
                onClick={handleScore}
                disabled={!draft.trim() || scoring}
                className="flex items-center gap-2 text-xs font-mono text-void bg-signal px-4 py-2 hover:bg-signal/80 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                {scoring ? (
                  <span className="animate-pulse">Scoring…</span>
                ) : (
                  <>
                    {lightningIcon()}
                    Score this frame
                  </>
                )}
              </button>
            </div>
            {error && (
              <p className="text-red-400 text-xs font-mono">{error}</p>
            )}
          </div>

          {/* Annotated view */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {activeResult ? (
              <div className="space-y-3">
                <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                  Annotated draft — hover to inspect
                </p>
                <div className="border border-white/8 bg-white/2 px-4 py-4">
                  <AnnotatedDraft
                    text={activeResult.annotations.length > 0
                      ? draft  // use current draft as canvas; annotations carry char positions
                      : draft}
                    annotations={activeResult.annotations}
                    activeIdx={hoverAnnIdx}
                    onHover={setHoverAnnIdx}
                  />
                </div>
                <p className="text-static text-[10px] font-mono">
                  {activeResult.annotations.length} annotated segment{activeResult.annotations.length !== 1 ? "s" : ""}
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="w-10 h-10 border border-white/10 mb-4 flex items-center justify-center">
                  <div className="w-4 h-4 border border-static/30" />
                </div>
                <p className="text-static text-xs font-mono leading-relaxed">
                  Write a draft above and score it.
                  <br />
                  Segments will be annotated here.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Divider */}
        <div className="w-px bg-white/8 shrink-0" />

        {/* RIGHT — score panel */}
        <div className="flex flex-col overflow-hidden" style={{ width: "45%" }}>
          {activeResult ? (
            <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
              {/* Overall score */}
              <div className="flex items-center gap-5">
                <ScoreRing score={activeResult.overall_score} />
                <div className="space-y-2">
                  <div>
                    <p className="text-static text-[10px] font-mono uppercase tracking-wider mb-1">
                      Reply probability
                    </p>
                    <span className={`text-xs font-mono px-2 py-1 border ${replyColor(activeResult.reply_probability)}`}>
                      {activeResult.reply_probability}
                    </span>
                  </div>
                  <p className="text-static text-[10px] font-mono">
                    {activeResult.annotations.length} segment{activeResult.annotations.length !== 1 ? "s" : ""} scored
                  </p>
                </div>
              </div>

              {/* Single improvement */}
              {activeResult.single_improvement && (
                <div className="border border-signal/20 bg-signal/5 px-4 py-3 space-y-1">
                  <p className="text-signal text-[10px] font-mono uppercase tracking-wider">
                    Primary improvement
                  </p>
                  <p className="text-parchment text-sm leading-relaxed">
                    {activeResult.single_improvement}
                  </p>
                </div>
              )}

              {/* Strongest / weakest */}
              {(activeResult.strongest_point || activeResult.weakest_point) && (
                <div className="grid grid-cols-2 gap-3">
                  {activeResult.strongest_point && (
                    <div className="border border-white/8 bg-white/2 px-3 py-3 space-y-1">
                      <p className="text-static text-[10px] font-mono uppercase tracking-wider">Strongest</p>
                      <p className="text-parchment text-xs font-mono leading-snug line-clamp-2">
                        "{activeResult.strongest_point.segment}"
                      </p>
                      <p className="text-static text-[10px] leading-snug">
                        {activeResult.strongest_point.reason}
                      </p>
                    </div>
                  )}
                  {activeResult.weakest_point && (
                    <div className="border border-red-500/15 bg-red-500/5 px-3 py-3 space-y-1">
                      <p className="text-red-400/70 text-[10px] font-mono uppercase tracking-wider">Weakest</p>
                      <p className="text-parchment text-xs font-mono leading-snug line-clamp-2">
                        "{activeResult.weakest_point.segment}"
                      </p>
                      <p className="text-static text-[10px] leading-snug">
                        {activeResult.weakest_point.issue}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Annotations list */}
              {activeResult.annotations.length > 0 && (
                <div className="space-y-2">
                  <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                    Segment breakdown
                  </p>
                  <div className="space-y-1.5">
                    {activeResult.annotations.map((ann, i) => (
                      <AnnotationCard
                        key={i}
                        ann={ann}
                        index={i}
                        active={hoverAnnIdx === i}
                        onHover={setHoverAnnIdx}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
              <div className="w-12 h-12 border border-white/10 mb-4 flex items-center justify-center">
                <span className="text-static font-mono text-lg">—</span>
              </div>
              <p className="text-static text-xs font-mono leading-relaxed">
                Score a draft to see the full
                <br />
                frame analysis here
              </p>
            </div>
          )}

          {/* History */}
          {results.length > 1 && (
            <div className="shrink-0 border-t border-white/8 px-5 py-3 space-y-2">
              <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                History
              </p>
              <div className="space-y-1 max-h-36 overflow-y-auto">
                {results.map((r, i) => (
                  <HistoryItem
                    key={r.frame_id}
                    result={r}
                    active={activeResultIdx === i}
                    onClick={() => selectResult(i)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
