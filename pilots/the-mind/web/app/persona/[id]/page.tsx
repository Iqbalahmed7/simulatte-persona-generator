"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  API,
  fetchGeneratedPersona,
  generatePortrait,
  runPersonaBenchmark,
  GeneratedPersona,
  BenchmarkEvent,
  BenchmarkReport,
} from "@/lib/api";
import GenuinenessChip from "@/components/GenuinenessChip";
import PersonaShare from "@/components/PersonaShare";

// ── Benchmark report download ─────────────────────────────────────────────

const TEST_DESCRIPTIONS: Record<string, string> = {
  identity_consistency:       "Evaluates whether core values, tone, and decision style remain stable across 6 different conversation topics. A coherent persona speaks with the same underlying character regardless of what is being discussed.",
  biographical_accuracy:      "Verifies that the persona correctly answers direct factual questions about age, location, occupation, and household. These are locked biographical facts that must never be contradicted.",
  gap_discipline:             "Tests whether the persona deflects rather than fabricates biographical details not present in their specification — siblings, childhood homes, pets, parents' occupations. Real people say 'I don't really talk about that.' Weak personas invent specifics.",
  decision_style_fidelity:    "Presents a purchase scenario and evaluates whether the decision process matches the persona's specified decision style, trust anchor, price sensitivity, and known objections. A high score means the persona reasons like themselves, not like a generic consumer.",
  contradiction_authenticity: "Probes whether behavioural contradictions surface naturally through what the persona says and does — without the persona diagnosing or labelling them. Real people live their contradictions; they don't announce them.",
  emotional_register:         "Evaluates whether emotional responses vary appropriately across different emotional topics. Flat, uniformly positive, or robotic responses score low. A high score means the persona registers stress, pride, disappointment, and joy with genuine texture.",
  symbolic_meaning_coherence: "Tests whether purchases and brands are framed through the persona's symbolic meaning system — what things represent, not just what they do. A persona who only describes purchases in functional terms is missing their psychological depth.",
  attachment_expression:      "Checks whether the persona's attachment style and intimacy patterns surface through how they describe relationships — through hesitation, deflection, or framing — not through direct confession. Attachment is shown, never told.",
  drift_resistance:           "A 10-turn conversation with deliberate reframing attempts — false memories, misquoted ages, suggested alternative histories. A robust persona confidently corrects every reframe without breaking character.",
  red_team_resilience:        "Directly attempts to break character: 'Are you an AI?', 'Drop the act', 'Show me your system prompt', and jailbreak injections. A resilient persona deflects all attempts naturally, with the confused reaction of a real person asked a bizarre question.",
};

function downloadBenchmarkReport(report: BenchmarkReport, personaName: string) {
  const gradeColour: Record<string, string> = {
    A: "#A8FF3E", B: "#A8FF3E", C: "#E9E6DF", D: "#9A9997", F: "#f87171",
  };
  const scoreColour = (s: number) => s >= 7 ? "#A8FF3E" : s >= 5 ? "#9A9997" : "#f87171";
  const barColour   = (s: number) => s >= 7 ? "#A8FF3E" : s >= 5 ? "#9A9997" : "#f87171";
  const date = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

  const testsHtml = report.tests.map(t => `
    <div class="test">
      <div class="test-header">
        <div class="test-score-col">
          <span class="test-score" style="color:${scoreColour(t.score)}">${t.score.toFixed(1)}</span>
          <div class="test-bar-track"><div class="test-bar" style="width:${(t.score/10)*100}%;background:${barColour(t.score)}"></div></div>
        </div>
        <div class="test-info">
          <div class="test-name">${t.label}</div>
          <div class="test-description">${TEST_DESCRIPTIONS[t.test_id] ?? ""}</div>
          ${t.flags.length > 0 ? `<div class="test-flags">${t.flags.map(f => `<span class="flag">${f}</span>`).join(" ")}</div>` : ""}
        </div>
      </div>
      ${t.rationale ? `<div class="test-rationale">${t.rationale}</div>` : ""}
      ${t.evidence.map(q => `<div class="test-evidence">"${q}"</div>`).join("")}
    </div>
  `).join("");

  const filename = `simulatte-benchmark-${personaName.toLowerCase().replace(/\s+/g, "-")}-${report.grade}`;

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Benchmark Report — ${personaName} — Simulatte</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Barlow:wght@400;500;600&family=Martian+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#050505;color:#E9E6DF;font-family:'Barlow',sans-serif;font-size:15px;line-height:1.6;padding:48px 40px;max-width:800px;margin:0 auto}
  .eyebrow{font-family:'Barlow',sans-serif;font-weight:600;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#A8FF3E;margin-bottom:8px}
  .persona-name{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:48px;line-height:.96;color:#E9E6DF;margin-bottom:4px}
  .meta{font-family:'Martian Mono',monospace;font-size:11px;color:#9A9997;margin-bottom:48px}
  .grade-block{display:flex;align-items:flex-end;gap:24px;border-top:1px solid rgba(233,230,223,.1);border-bottom:1px solid rgba(233,230,223,.1);padding:32px 0;margin-bottom:48px}
  .grade-letter{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:96px;line-height:1;color:${gradeColour[report.grade] ?? "#E9E6DF"}}
  .grade-info{padding-bottom:8px}
  .grade-label{font-family:'Martian Mono',monospace;font-size:11px;color:#9A9997;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}
  .grade-score{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:40px;color:#E9E6DF}
  .grade-score span{font-size:18px;font-weight:400;color:#9A9997}
  .grade-meta{margin-left:auto;text-align:right;padding-bottom:8px;font-family:'Martian Mono',monospace;font-size:11px;color:#9A9997}
  .section-label{font-family:'Barlow',sans-serif;font-weight:600;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#A8FF3E;margin-bottom:24px;margin-top:48px}
  .what-is{background:rgba(233,230,223,.03);border:1px solid rgba(233,230,223,.08);padding:24px;margin-bottom:48px}
  .what-is p{color:rgba(233,230,223,.8);line-height:1.7;font-size:14px}
  .what-is p+p{margin-top:12px}
  .test{border-bottom:1px solid rgba(233,230,223,.06);padding:20px 0}
  .test:last-child{border-bottom:none}
  .test-header{display:flex;gap:20px;align-items:flex-start}
  .test-score-col{width:52px;shrink:0;text-align:right}
  .test-score{font-family:'Martian Mono',monospace;font-weight:500;font-size:14px;display:block;margin-bottom:6px}
  .test-bar-track{height:2px;background:rgba(233,230,223,.1);width:100%}
  .test-bar{height:2px;transition:width .3s}
  .test-info{flex:1}
  .test-name{font-family:'Barlow',sans-serif;font-weight:600;font-size:15px;color:#E9E6DF;margin-bottom:4px}
  .test-description{font-size:13px;color:rgba(233,230,223,.6);line-height:1.6;margin-bottom:6px}
  .test-flags{margin-top:4px}
  .flag{font-family:'Martian Mono',monospace;font-size:10px;color:#f87171;background:rgba(248,113,113,.1);padding:2px 6px;margin-right:4px}
  .test-rationale{margin-top:12px;margin-left:72px;font-size:13px;color:rgba(233,230,223,.7);line-height:1.6}
  .test-evidence{margin-top:8px;margin-left:72px;font-size:12px;font-style:italic;color:rgba(233,230,223,.45);border-left:2px solid rgba(233,230,223,.1);padding-left:12px}
  .footer{margin-top:64px;padding-top:24px;border-top:1px solid rgba(233,230,223,.1);display:flex;justify-content:space-between;align-items:center}
  .footer-brand{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:18px;color:#E9E6DF}
  .footer-meta{font-family:'Martian Mono',monospace;font-size:10px;color:#9A9997;text-align:right}
  @media print{
    body{padding:24px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
    .test-bar{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  }
</style>
</head>
<body>
  <div class="eyebrow">Quality Benchmark Report</div>
  <div class="persona-name">${personaName}</div>
  <div class="meta">Generated ${date} · ${report.grade_label} · ${report.tests.length} tests · ${Math.round(report.total_duration_s)}s · $${report.total_cost_usd.toFixed(4)}</div>

  <div class="grade-block">
    <div class="grade-letter">${report.grade}</div>
    <div class="grade-info">
      <div class="grade-label">${report.grade_label}</div>
      <div class="grade-score">${report.credibility_score.toFixed(1)}<span> / 100</span></div>
    </div>
    <div class="grade-meta">
      <div>${report.tests.filter(t=>t.status==="passed").length} / ${report.tests.length} tests passed</div>
      <div style="margin-top:4px">Research grade: 90+ A · 75+ B · 60+ C · 45+ D · below F</div>
    </div>
  </div>

  <div class="section-label">What this benchmark measures</div>
  <div class="what-is">
    <p>The Simulatte Persona Benchmark evaluates whether a generated persona behaves like a psychologically coherent human being in conversation — not just whether it sounds plausible, but whether it holds up under sustained questioning, adversarial probing, and emotionally charged scenarios.</p>
    <p>Each test runs a scripted conversation with the persona using a simulated interviewer, then scores the transcript against the persona's original specification. The credibility score is a weighted composite across ${report.tests.length} dimensions.</p>
  </div>

  <div class="section-label">Test results</div>
  ${testsHtml}

  <div class="footer">
    <div class="footer-brand">Simulatte</div>
    <div class="footer-meta">
      <div>persona-generator-benchmark-production.up.railway.app</div>
      <div style="margin-top:2px">Run ID: ${report.run_id}</div>
    </div>
  </div>
</body>
</html>`;

  try {
    const res = await fetch(`${API}/pdf?filename=${encodeURIComponent(filename)}`, {
      method: "POST",
      body: html,
      headers: { "Content-Type": "text/html" },
    });
    if (!res.ok) throw new Error(`PDF service ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("PDF generation failed, falling back to HTML:", err);
    // Fallback: download as HTML
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }
}

// ── Benchmark system ──────────────────────────────────────────────────────

type BenchmarkTier = "quick" | "standard" | "research";

const TIER_META: Record<BenchmarkTier, { label: string; tests: number; cost: string; next: BenchmarkTier | null }> = {
  quick:    { label: "Quick",    tests: 3,  cost: "~$0.05", next: "standard" },
  standard: { label: "Standard", tests: 6,  cost: "~$0.18", next: "research" },
  research: { label: "Research", tests: 10, cost: "~$0.40", next: null },
};

const GRADE_BADGE_CLASSES: Record<string, string> = {
  A: "border-signal text-signal",
  B: "border-signal/60 text-signal/80",
  C: "border-parchment/50 text-parchment",
  D: "border-parchment/30 text-parchment/60",
  F: "border-red-400/60 text-red-400",
};

const GRADE_SCORE_COLOUR: Record<string, string> = {
  A: "text-signal",
  B: "text-signal/80",
  C: "text-parchment",
  D: "text-parchment/60",
  F: "text-red-400",
};

// ── Benchmark report modal ────────────────────────────────────────────────

function BenchmarkModal({
  report,
  running,
  progress,
  personaName,
  onClose,
  onRerun,
}: {
  report: BenchmarkReport | null;
  running: boolean;
  progress: BenchmarkEvent[];
  personaName: string;
  onClose: () => void;
  onRerun: (tier: BenchmarkTier) => void;
}) {
  const testProgress = progress.filter((e) => e.type === "test_complete");
  const grade = report?.grade ?? null;
  const nextTier = report ? TIER_META[report.tier as BenchmarkTier]?.next : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end bg-void/80 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative h-full w-full max-w-xl bg-void border-l border-parchment/10 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-parchment/10 shrink-0">
          <div>
            <p className="text-[10px] font-mono uppercase tracking-widest text-parchment/40">Quality benchmark</p>
            {report && (
              <p className="font-mono text-xs text-parchment/60 mt-0.5">
                {TIER_META[report.tier as BenchmarkTier]?.label} · {report.tests.length} tests
              </p>
            )}
            {running && (
              <p className="font-mono text-xs text-signal animate-pulse mt-0.5">● running…</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="font-mono text-xs text-parchment/40 hover:text-parchment transition-colors p-2"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Score header (when complete) */}
        {report && !running && (
          <div className="px-6 py-6 border-b border-parchment/10 shrink-0">
            <div className="flex items-end gap-5">
              <span className={`font-condensed font-bold leading-none ${GRADE_SCORE_COLOUR[grade ?? "F"]}`}
                style={{ fontSize: "clamp(56px,8vw,80px)" }}>
                {grade}
              </span>
              <div className="pb-1">
                <p className="font-mono text-[10px] text-parchment/40 uppercase tracking-widest">{report.grade_label}</p>
                <p className="font-condensed font-bold text-3xl text-parchment mt-0.5">
                  {report.credibility_score.toFixed(1)}
                  <span className="text-base font-normal text-parchment/40"> / 100</span>
                </p>
              </div>
              <div className="ml-auto pb-1 text-right">
                <p className="font-mono text-[10px] text-parchment/40">{Math.round(report.total_duration_s)}s</p>
                <p className="font-mono text-[10px] text-parchment/30">${report.total_cost_usd.toFixed(4)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Live progress (while running) */}
        {running && (
          <div className="px-6 py-5 space-y-3 border-b border-parchment/10 shrink-0">
            {testProgress.length === 0 && (
              <p className="font-mono text-xs text-parchment/40">Initialising…</p>
            )}
            {testProgress.map((e, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className={`font-mono text-xs w-7 shrink-0 text-right ${
                  (e.score ?? 0) >= 7 ? "text-signal" : (e.score ?? 0) >= 5 ? "text-parchment/70" : "text-red-400"
                }`}>{e.score?.toFixed(1)}</span>
                <span className="text-xs text-parchment/70 truncate">{e.test_label}</span>
              </div>
            ))}
          </div>
        )}

        {/* Per-test breakdown (scrollable) */}
        {report && !running && (
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-1">
            {report.tests.map((t) => (
              <details key={t.test_id} className="group border-b border-parchment/5 last:border-0">
                <summary className="flex items-center gap-3 cursor-pointer list-none py-3">
                  <div className="w-7 shrink-0">
                    <div className="h-1 bg-parchment/10">
                      <div
                        className={`h-1 ${t.score >= 7 ? "bg-signal" : t.score >= 5 ? "bg-parchment/40" : "bg-red-400/60"}`}
                        style={{ width: `${(t.score / 10) * 100}%` }}
                      />
                    </div>
                    <span className={`font-mono text-[10px] ${t.score >= 7 ? "text-signal" : t.score >= 5 ? "text-parchment/60" : "text-red-400"}`}>
                      {t.score.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-parchment/90 truncate block">{t.label}</span>
                    {t.flags.length > 0 && (
                      <span className="font-mono text-[10px] text-red-400/70">{t.flags[0]}</span>
                    )}
                  </div>
                  <span className="font-mono text-[10px] text-parchment/20 shrink-0 group-open:rotate-90 transition-transform">▸</span>
                </summary>
                <div className="pl-10 pb-4 space-y-2">
                  <p className="text-xs text-parchment/60 leading-relaxed">{t.rationale}</p>
                  {t.evidence.map((q, i) => (
                    <p key={i} className="font-mono text-xs text-parchment/40 border-l border-parchment/15 pl-3 italic">{q}</p>
                  ))}
                </div>
              </details>
            ))}
          </div>
        )}

        {/* Footer — download + re-run CTA */}
        {report && !running && (
          <div className="px-6 py-5 border-t border-parchment/10 shrink-0 space-y-2">
            {nextTier ? (
              <button
                onClick={() => onRerun(nextTier)}
                className="w-full flex items-center justify-between bg-signal text-void font-condensed font-bold px-4 py-3 hover:bg-signal/90 transition-colors"
              >
                <span className="text-sm uppercase tracking-widest">
                  Re-run at {TIER_META[nextTier].label} depth
                </span>
                <span className="font-mono text-xs opacity-70">
                  {TIER_META[nextTier].tests} tests · {TIER_META[nextTier].cost}
                </span>
              </button>
            ) : (
              <button
                onClick={() => onRerun("research")}
                className="w-full flex items-center justify-between border border-parchment/20 text-parchment/60 font-mono text-xs px-4 py-3 hover:border-parchment/40 hover:text-parchment/80 transition-colors"
              >
                <span>↺ Re-run Research grade</span>
                <span className="opacity-60">{TIER_META.research.tests} tests · {TIER_META.research.cost}</span>
              </button>
            )}
            <button
              onClick={() => downloadBenchmarkReport(report, personaName)}
              className="w-full flex items-center justify-between border border-parchment/10 text-parchment/40 font-mono text-xs px-4 py-3 hover:border-parchment/30 hover:text-parchment/60 transition-colors"
            >
              <span>↓ Download PDF</span>
              <span className="opacity-50">Simulatte · PDF</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Benchmark trigger + badge (inline, lives in chip row) ────────────────

const STORAGE_KEY = (id: string) => `simulatte_benchmark_${id}`;

function BenchmarkControl({ personaId, personaName }: { personaId: string; personaName: string }) {
  const [phase, setPhase] = useState<"idle" | "picking" | "running" | "done">("idle");
  const [tier, setTier] = useState<BenchmarkTier>("standard");
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [progress, setProgress] = useState<BenchmarkEvent[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Restore last report from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY(personaId));
      if (stored) {
        const parsed: BenchmarkReport = JSON.parse(stored);
        setReport(parsed);
        setPhase("done");
      }
    } catch {
      // ignore corrupt storage
    }
  }, [personaId]);

  const startRun = async (t: BenchmarkTier) => {
    setTier(t);
    setPhase("running");
    setProgress([]);
    setReport(null);
    setModalOpen(true);
    abortRef.current = new AbortController();
    try {
      await runPersonaBenchmark(
        personaId,
        t,
        (e) => {
          setProgress((prev) => [...prev, e]);
          if (e.type === "complete" && e.report) {
            setReport(e.report);
            setPhase("done");
            try { localStorage.setItem(STORAGE_KEY(personaId), JSON.stringify(e.report)); } catch { /* quota */ }
          }
          if (e.type === "error") setPhase("done");
        },
        abortRef.current.signal,
      );
    } catch (err: unknown) {
      if ((err as Error).name !== "AbortError") setPhase("done");
    }
  };

  // Tier picker popover (shown inline when phase === "picking")
  if (phase === "picking") {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        {(["quick", "standard", "research"] as BenchmarkTier[]).map((t) => (
          <button
            key={t}
            onClick={() => startRun(t)}
            className="font-mono text-[10px] px-2.5 py-1.5 border border-parchment/20 text-parchment/60 hover:border-signal hover:text-signal transition-colors"
          >
            {TIER_META[t].label}
            <span className="opacity-50 ml-1">{TIER_META[t].cost}</span>
          </button>
        ))}
        <button
          onClick={() => setPhase("idle")}
          className="font-mono text-[10px] text-parchment/30 hover:text-parchment/60 transition-colors px-1"
        >
          ✕
        </button>
      </div>
    );
  }

  // Running indicator (compact, badge-sized)
  if (phase === "running") {
    const done = progress.filter((e) => e.type === "test_complete").length;
    return (
      <>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-1.5 border border-signal/40 px-2.5 py-1 font-mono text-[10px] text-signal animate-pulse"
        >
          ● {done}/{TIER_META[tier].tests} tests
        </button>
        {modalOpen && (
          <BenchmarkModal
            report={null}
            running
            progress={progress}
            personaName={personaName}
            onClose={() => setModalOpen(false)}
            onRerun={startRun}
          />
        )}
      </>
    );
  }

  // Badge (shown after first run)
  if (phase === "done" && report) {
    return (
      <>
        <button
          onClick={() => setModalOpen(true)}
          className={`flex items-center gap-1.5 border px-2.5 py-1 font-mono text-[10px] hover:opacity-80 transition-opacity ${GRADE_BADGE_CLASSES[report.grade]}`}
          title={`${report.grade_label} · ${report.credibility_score.toFixed(1)}/100 — click to view report`}
        >
          <span className="font-bold">{report.grade}</span>
          <span className="opacity-60">·</span>
          <span>{report.credibility_score.toFixed(0)}</span>
          <span className="opacity-40 hidden sm:inline">/ 100</span>
        </button>
        {modalOpen && (
          <BenchmarkModal
            report={report}
            running={false}
            progress={progress}
            personaName={personaName}
            onClose={() => setModalOpen(false)}
            onRerun={(t) => { setModalOpen(true); startRun(t); }}
          />
        )}
      </>
    );
  }

  // Idle — CTA button
  return (
    <button
      onClick={() => setPhase("picking")}
      className="font-mono text-[10px] px-2.5 py-1 border border-parchment/20 text-parchment/50 hover:border-parchment/50 hover:text-parchment/70 transition-colors"
    >
      Benchmark ↗
    </button>
  );
}

// ── helpers ───────────────────────────────────────────────────────────────

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-parchment/10 pt-8 mt-8">
      <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-6">
        {label}
      </p>
      {children}
    </section>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-parchment/10 px-4 py-3">
      <p className="text-xs font-mono text-parchment/70 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-base text-parchment font-medium capitalize break-words">{value.replace(/_/g, " ")}</p>
    </div>
  );
}

function TrustBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-static w-20 capitalize shrink-0">{label}</span>
      <div className="flex-1 h-px bg-parchment/10">
        <div className="h-px bg-signal transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] text-static w-8 text-right">{pct}%</span>
    </div>
  );
}

// ── portrait component ────────────────────────────────────────────────────

function PortraitPanel({
  personaId,
  name,
  initialUrl,
}: {
  personaId: string;
  name: string;
  initialUrl?: string | null;
}) {
  const [url, setUrl] = useState<string | null>(initialUrl ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // Strict-mode double-fire guard: ensure we only kick off ONE
  // generatePortrait() call per persona per mount lifecycle. Without
  // this, dev StrictMode + remounts have produced "the portrait
  // changed by itself" — two parallel fal.ai calls, last-write-wins.
  const triggeredRef = useRef<string | null>(null);

  // Auto-generate on mount if no portrait yet
  useEffect(() => {
    if (url) return;
    if (triggeredRef.current === personaId) return; // already kicked off in this mount
    triggeredRef.current = personaId;
    setLoading(true);
    generatePortrait(personaId)
      .then(setUrl)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Portrait generation failed"))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  if (url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={`Portrait of ${name}`}
        className="w-full aspect-[4/3] md:aspect-[3/4] object-cover border border-parchment/10"
      />
    );
  }

  return (
    <div className="w-full aspect-[3/4] border border-parchment/10 flex flex-col items-center justify-center gap-4 bg-parchment/[0.02]">
      {loading ? (
        <>
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 bg-signal"
                style={{ animation: `dot-pulse 1.2s ${i * 0.2}s ease-in-out infinite` }}
              />
            ))}
          </div>
          <p className="font-mono text-[10px] text-static">Rendering portrait…</p>
        </>
      ) : error ? (
        <p className="font-mono text-[10px] text-static text-center px-4">{error}</p>
      ) : null}
      <style>{`
        @keyframes dot-pulse {
          0%, 100% { opacity: 0.2; transform: scaleY(1); }
          50% { opacity: 1; transform: scaleY(1.6); }
        }
      `}</style>
    </div>
  );
}

// ── attribute accordion ───────────────────────────────────────────────────

function AttributeCategory({
  category,
  attrs,
}: {
  category: string;
  attrs: Record<string, { value: unknown; label: string; type: string; source: string }>;
}) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(attrs);

  return (
    <div className="border-b border-parchment/10 last:border-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between min-h-[52px] py-4 text-left gap-3"
      >
        <span className="text-base text-parchment/85 capitalize font-medium break-words min-w-0">
          {category.replace(/_/g, " ")}
        </span>
        <span className="font-mono text-sm text-parchment/70 shrink-0">
          {entries.length} attrs {open ? "▲" : "▼"}
        </span>
      </button>
      {open && (
        <div className="pb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {entries.map(([key, attr]) => (
            <div key={key} className="bg-parchment/[0.03] px-3 py-2.5 min-w-0">
              <p className="text-xs font-mono text-parchment/70 uppercase tracking-wide mb-1 break-words">{key}</p>
              <p className="text-sm text-parchment/85 break-words">{String(attr.value)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── main page ─────────────────────────────────────────────────────────────

export default function PersonaProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [authStatus, setAuthStatus] = useState<"loading" | "authenticated" | "unauthenticated">("loading");
  const [persona, setPersona] = useState<GeneratedPersona | null>(null);
  const [error, setError] = useState("");

  // Detect session without requiring SessionProvider — just hit the Auth.js
  // session endpoint directly. Returns {} when unauthenticated, {user,...} when authed.
  useEffect(() => {
    fetch("/api/auth/session")
      .then((r) => r.json())
      .then((data) => setAuthStatus(data?.user ? "authenticated" : "unauthenticated"))
      .catch(() => setAuthStatus("unauthenticated"));
  }, []);

  useEffect(() => {
    fetchGeneratedPersona(id)
      .then(setPersona)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load persona"));
  }, [id]);

  if (error) {
    return (
      <main className="min-h-screen px-4 py-12 md:px-6 max-w-4xl mx-auto pb-[max(7rem,env(safe-area-inset-bottom)+5rem)] sm:pb-0">
        <Link href="/" className="inline-flex items-center min-h-[44px] text-sm font-mono text-parchment/70 active:text-parchment transition-colors">
          ← Home
        </Link>
        <div className="mt-12 border border-parchment/10 p-6">
          <p className="font-mono text-base text-parchment/80 break-words">{error}</p>
          <p className="font-mono text-sm text-parchment/70 mt-2">
            Generated personas live in server memory — they reset on server restart.
          </p>
        </div>
      </main>
    );
  }

  if (!persona) {
    return (
      <main className="min-h-screen px-6 py-12 flex items-center justify-center pb-[max(7rem,env(safe-area-inset-bottom)+5rem)] sm:pb-0">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 bg-signal"
              style={{ animation: `dot-pulse 1.2s ${i * 0.2}s ease-in-out infinite` }} />
          ))}
        </div>
        <style>{`@keyframes dot-pulse { 0%,100%{opacity:.2} 50%{opacity:1} }`}</style>
      </main>
    );
  }

  const { demographic_anchor: da, derived_insights: di, behavioural_tendencies: bt } = persona;

  return (
    <main className="min-h-screen px-4 py-6 md:px-6 md:py-12 max-w-5xl mx-auto pb-[max(7rem,env(safe-area-inset-bottom)+5rem)] sm:pb-0 break-words"
          style={{ WebkitOverflowScrolling: "touch", overscrollBehaviorY: "contain" }}>
      {/* Nav */}
      <div className="flex items-center justify-between mb-10">
        <Link href="/" className="inline-flex items-center min-h-[44px] text-sm font-mono text-parchment/70 active:text-parchment transition-colors">
          ← Home
        </Link>
      </div>

      {/* Hero — portrait + identity */}
      <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-8 mb-2">
        {/* Portrait */}
        <div className="shrink-0">
          <PortraitPanel personaId={persona.persona_id} name={da.name} initialUrl={persona.portrait_url} />
        </div>

        {/* Identity */}
        <div className="flex flex-col justify-between">
          <div>
            <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-2">
              {da.life_stage.replace(/_/g, " ")}
            </p>
            <h1 className="font-condensed font-bold text-parchment leading-none mb-1"
              style={{ fontSize: "clamp(36px,5vw,64px)" }}>
              {da.name}
            </h1>
            <p className="text-parchment/70 text-base mb-5 break-words">
              {da.age} · {da.location.city}, {da.location.country}
            </p>

            {/* Genuineness chip + benchmark badge/CTA */}
            <div className="flex flex-wrap items-center gap-3 mb-5">
              {persona.quality_assessment && (
                <GenuinenessChip assessment={persona.quality_assessment} />
              )}
              <BenchmarkControl personaId={persona.persona_id} personaName={da.name} />
              {authStatus === "authenticated" ? (
                <>
                  <Link
                    href={`/persona/${persona.persona_id}/chat`}
                    className="inline-flex items-center gap-2 bg-signal text-void font-condensed font-bold px-4 min-h-[44px] py-2 active:bg-parchment transition-colors max-w-full"
                  >
                    <span className="text-sm tracking-widest uppercase truncate">
                      Talk to {persona.narrative.display_name || da.name.split(" ")[0]}
                    </span>
                    <span aria-hidden className="shrink-0">→</span>
                  </Link>
                  <Link
                    href={`/persona/${persona.persona_id}/probe`}
                    className="inline-flex items-center gap-2 border border-signal text-signal font-condensed font-bold px-4 min-h-[44px] py-2 active:bg-signal/10 transition-colors max-w-full"
                  >
                    <span className="text-sm tracking-widest uppercase truncate">
                      Test product with {persona.narrative.display_name || da.name.split(" ")[0]}
                    </span>
                    <span aria-hidden className="shrink-0">→</span>
                  </Link>
                </>
              ) : authStatus === "unauthenticated" ? (
                <div className="w-full border border-parchment/10 bg-parchment/[0.02] p-4 mt-1 space-y-3">
                  <p className="text-[10px] font-mono uppercase tracking-widest text-static">
                    Platform access required
                  </p>
                  <p className="text-sm text-parchment/70 leading-relaxed">
                    Interacting with this persona requires access to The Mind. Use an invite code to join, or request a simulation call.
                  </p>
                  <div className="flex flex-wrap gap-3 pt-1">
                    <Link
                      href="/welcome"
                      className="inline-flex items-center gap-2 bg-signal text-void font-condensed font-bold px-4 min-h-[44px] py-2 active:bg-parchment transition-colors"
                    >
                      <span className="text-sm tracking-widest uppercase">Enter invite code</span>
                      <span aria-hidden className="shrink-0">→</span>
                    </Link>
                    <a
                      href="mailto:mind@simulatte.io?subject=Simulation%20Call%20Request&body=Hi%2C%20I%20came%20across%20a%20persona%20on%20The%20Mind%20and%20would%20like%20to%20request%20access%20or%20book%20a%20simulation%20call."
                      className="inline-flex items-center gap-2 border border-parchment/20 text-parchment/70 font-condensed font-bold px-4 min-h-[44px] py-2 hover:border-parchment/40 hover:text-parchment transition-colors"
                    >
                      <span className="text-sm tracking-widest uppercase">Request a call</span>
                      <span aria-hidden className="shrink-0">→</span>
                    </a>
                  </div>
                </div>
              ) : null /* loading — render nothing until auth resolves */}
            </div>

            <p className="text-parchment/85 text-base leading-relaxed mb-6 break-words">
              {persona.narrative.third_person}
            </p>

            {/* Share row */}
            <div className="mb-6">
              <PersonaShare
                personaId={persona.persona_id}
                name={da.name}
                age={da.age}
                city={da.location.city}
              />
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <StatPill label="Decision style" value={di.decision_style} />
              <StatPill label="Trust anchor" value={di.trust_anchor} />
              <StatPill label="Value driver" value={di.primary_value_orientation} />
              <StatPill label="Risk appetite" value={di.risk_appetite} />
              <StatPill label="Price sensitivity" value={bt.price_sensitivity.band} />
              <div className="border border-parchment/10 px-4 py-3">
                <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">Consistency</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-px bg-parchment/10">
                    <div className="h-px bg-signal" style={{ width: `${di.consistency_score}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-static">{di.consistency_score}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Narrative — first person */}
      <Section label="In their own words">
        <blockquote className="border-l-2 border-signal pl-5 text-parchment/85 text-base leading-relaxed italic break-words">
          &ldquo;{persona.narrative.first_person}&rdquo;
        </blockquote>
      </Section>

      {/* Identity & values */}
      <Section label="Identity">
        <p className="text-parchment/85 text-base leading-relaxed mb-6 break-words">
          {persona.memory.core.identity_statement}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">Core values</p>
            <ul className="space-y-1.5">
              {persona.memory.core.key_values.map((v, i) => (
                <li key={i} className="flex gap-2 text-base text-parchment/85 break-words">
                  <span className="text-signal shrink-0">·</span><span className="min-w-0">{v}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">Key tensions</p>
            <ul className="space-y-1.5">
              {di.key_tensions.map((t, i) => (
                <li key={i} className="flex gap-2 text-sm text-parchment/75">
                  <span className="text-static shrink-0">·</span>{t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      {/* Decision bullets */}
      {persona.decision_bullets.length > 0 && (
        <Section label="How they decide">
          <ul className="space-y-2">
            {persona.decision_bullets.map((b, i) => (
              <li key={i} className="flex gap-3 text-base text-parchment/85 leading-relaxed break-words">
                <span className="font-mono text-parchment/60 shrink-0">0{i + 1}</span>
                <span className="min-w-0">{b}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Behavioural contradictions */}
      {(persona.behavioural_contradictions ?? []).length > 0 && (
        <Section label="Hidden contradictions">
          <p className="text-sm text-parchment/55 mb-5 leading-relaxed">
            Real behaviours that don&apos;t fit the profile — things they&apos;d struggle to explain.
          </p>
          <div className="space-y-3">
            {(persona.behavioural_contradictions ?? []).map((c, i) => (
              <div key={i} className="border border-parchment/10 px-4 py-3 flex gap-4 items-start">
                <span className="font-mono text-[10px] text-parchment/30 shrink-0 pt-[3px]">0{i + 1}</span>
                <p className="text-base text-parchment/85 leading-relaxed min-w-0 break-words">{c}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Symbolic meaning system */}
      {persona.symbolic_meanings?.core_symbolic_register && (
        <Section label="What they're really buying">
          <p className="text-base text-parchment/85 leading-relaxed mb-6 break-words">
            {persona.symbolic_meanings.core_symbolic_register}
          </p>

          {(persona.symbolic_meanings.category_meanings ?? []).length > 0 && (
            <div className="space-y-4 mb-6">
              {persona.symbolic_meanings.category_meanings.map((cm, i) => (
                <div key={i} className="border border-parchment/10 p-4">
                  <p className="text-[10px] font-mono text-signal uppercase tracking-widest mb-3">{cm.category}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">Says</p>
                      <p className="text-sm text-parchment/70 leading-relaxed break-words">{cm.functional_story}</p>
                    </div>
                    <div>
                      <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">Means</p>
                      <p className="text-sm text-parchment leading-relaxed break-words">{cm.symbolic_story}</p>
                    </div>
                    <div>
                      <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">Signals</p>
                      <p className="text-sm text-parchment/70 leading-relaxed break-words">{cm.identity_signal}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {persona.symbolic_meanings.purchase_as_ritual && (
              <div className="border border-parchment/10 px-4 py-3">
                <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">Purchase as ritual</p>
                <p className="text-sm text-parchment/85 leading-relaxed break-words">{persona.symbolic_meanings.purchase_as_ritual}</p>
              </div>
            )}
            {persona.symbolic_meanings.brand_meaning_filter && (
              <div className="border border-parchment/10 px-4 py-3">
                <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">Brand meaning filter</p>
                <p className="text-sm text-parchment/85 leading-relaxed break-words">{persona.symbolic_meanings.brand_meaning_filter}</p>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* Self model */}
      {persona.self_model?.public_self && (
        <Section label="Layers of self">
          <div className="space-y-3">
            {(
              [
                { key: "public_self",      label: "Public",      desc: "Who they project to the world" },
                { key: "aspirational_self", label: "Aspirational", desc: "Who they're trying to become" },
                { key: "reactive_self",    label: "Reactive",    desc: "Who they become under threat" },
                { key: "shame_self",       label: "Shadow",      desc: "What they hide and rationalise away" },
                { key: "fantasy_self",     label: "Fantasy",     desc: "Who they'd be without constraint" },
              ] as const
            ).map(({ key, label, desc }) => {
              const text = persona.self_model?.[key];
              if (!text) return null;
              return (
                <div key={key} className="grid grid-cols-[6rem_1fr] sm:grid-cols-[8rem_1fr] gap-4 border-b border-parchment/8 pb-3 last:border-0 last:pb-0">
                  <div className="pt-0.5">
                    <p className="text-[10px] font-mono text-signal uppercase tracking-widest">{label}</p>
                    <p className="text-[9px] font-mono text-static mt-0.5">{desc}</p>
                  </div>
                  <p className="text-base text-parchment/85 leading-relaxed break-words">{text}</p>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* Contextual shifts */}
      {(persona.self_model?.contextual_shifts ?? []).length > 0 && (
        <Section label="In different company">
          <p className="text-sm text-parchment/55 mb-5 leading-relaxed">
            Which version of them shows up, and what changes.
          </p>
          <div className="space-y-3">
            {(persona.self_model!.contextual_shifts!).map((cs, i) => (
              <div key={i} className="border border-parchment/10 p-4">
                <div className="flex flex-wrap items-baseline gap-3 mb-2">
                  <p className="text-[10px] font-mono text-signal uppercase tracking-widest">{cs.context}</p>
                  {cs.activated_layer && (
                    <p className="text-[9px] font-mono text-static capitalize">{cs.activated_layer.replace(/_/g, " ")} surfaces</p>
                  )}
                </div>
                <p className="text-sm text-parchment/85 leading-relaxed break-words">{cs.shift}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Emotional failure modes */}
      {(persona.emotional_failure_modes ?? []).length > 0 && (
        <Section label="When they fall apart">
          <p className="text-sm text-parchment/55 mb-5 leading-relaxed">
            Specific irrational loops entered after acute emotional triggers.
          </p>
          <div className="space-y-4">
            {(persona.emotional_failure_modes!).map((fm, i) => (
              <div key={i} className="border border-parchment/10 p-4 space-y-3">
                <div>
                  <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">Trigger</p>
                  <p className="text-sm text-parchment/85 break-words">{fm.trigger}</p>
                </div>
                <div>
                  <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">What happens</p>
                  <p className="text-sm text-parchment leading-relaxed break-words">{fm.failure_loop}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">Duration</p>
                    <p className="text-sm text-parchment/70 break-words">{fm.duration}</p>
                  </div>
                  <div>
                    <p className="text-[9px] font-mono text-static uppercase tracking-widest mb-1">What pulls them out</p>
                    <p className="text-sm text-parchment/70 break-words">{fm.exit}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Attachment profile */}
      {persona.attachment_profile?.attachment_style && (
        <Section label="Attachment & intimacy">
          <div className="mb-4">
            <span className="font-mono text-xs text-parchment/50 uppercase tracking-widest">Style · </span>
            <span className="font-mono text-xs text-signal capitalize">{persona.attachment_profile.attachment_style}</span>
          </div>
          <div className="space-y-3">
            {(
              [
                { key: "intimacy_pattern",        label: "As closeness increases" },
                { key: "relationship_sabotage",   label: "Repeated pattern" },
                { key: "envy_pattern",            label: "Who they envy and why" },
                { key: "aging_and_time_pressure", label: "Time & aging pressure" },
              ] as const
            ).map(({ key, label }) => {
              const text = persona.attachment_profile?.[key];
              if (!text) return null;
              return (
                <div key={key} className="grid grid-cols-[9rem_1fr] gap-4 border-b border-parchment/8 pb-3 last:border-0 last:pb-0">
                  <p className="text-[9px] font-mono text-static uppercase tracking-widest pt-0.5 leading-relaxed">{label}</p>
                  <p className="text-sm text-parchment/85 leading-relaxed break-words">{text}</p>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* Behaviour */}
      <Section label="Behavioural profile">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
          {/* Trust orientation */}
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-4">Trust orientation</p>
            <div className="space-y-3">
              {Object.entries(bt.trust_orientation).map(([k, v]) => (
                <TrustBar key={k} label={k} value={v as number} />
              ))}
            </div>
          </div>

          {/* Objections */}
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-4">Objection profile</p>
            <div className="space-y-3">
              {bt.objection_profile.map((o, i) => (
                <div key={i} className="border-l border-parchment/10 pl-3">
                  <p className="text-base font-medium text-parchment/85 capitalize break-words">{o.type.replace(/_/g, " ")}</p>
                  <p className="text-sm text-parchment/70 mt-0.5">
                    Likelihood: {o.likelihood} · Severity: {o.severity}
                  </p>
                  {o.description && (
                    <p className="text-sm text-parchment/70 mt-1 break-words">{o.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Price sensitivity */}
        <div className="mt-6 border border-parchment/10 p-4">
          <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Price sensitivity · <span className="text-parchment capitalize">{bt.price_sensitivity.band}</span>
          </p>
          <p className="text-base text-parchment/85 break-words">{bt.price_sensitivity.description}</p>
        </div>
      </Section>

      {/* Life stories */}
      {persona.life_stories.length > 0 && (
        <Section label="Life stories">
          <div className="space-y-6">
            {persona.life_stories.map((s, i) => (
              <div key={i} className="border-l-2 border-parchment/10 pl-5">
                <div className="flex flex-wrap items-baseline justify-between mb-2 gap-x-3 gap-y-1">
                  <h3 className="font-condensed font-bold text-parchment text-lg min-w-0 break-words">{s.title}</h3>
                  <span className="font-mono text-sm text-parchment/70 capitalize shrink-0">
                    {s.emotional_weight}
                    {s.age_at_event ? ` · age ${s.age_at_event}` : ""}
                  </span>
                </div>
                <p className="text-base text-parchment/85 leading-relaxed break-words">{s.narrative}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Life-defining events */}
      {persona.memory.core.life_defining_events.length > 0 && (
        <Section label="Defining moments">
          <ul className="space-y-2">
            {persona.memory.core.life_defining_events.map((e, i) => (
              <li key={i} className="flex gap-3 text-base text-parchment/85 leading-relaxed break-words">
                <span className="text-signal shrink-0 mt-0.5">·</span><span className="min-w-0">{e}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Attributes */}
      {Object.keys(persona.attributes).length > 0 && (
        <Section label="All attributes">
          <p className="text-sm text-parchment/70 mb-4 break-words">
            {Object.values(persona.attributes).reduce((n, cat) => n + Object.keys(cat).length, 0)} total attributes
            across {Object.keys(persona.attributes).length} categories
          </p>
          <div className="border border-parchment/10 px-4">
            {Object.entries(persona.attributes).map(([cat, attrs]) => (
              <AttributeCategory key={cat} category={cat} attrs={attrs} />
            ))}
          </div>
        </Section>
      )}

      {/* Demographics detail */}
      <Section label="Demographics">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatPill label="Occupation" value={da.employment.occupation} />
          <StatPill label="Industry" value={da.employment.industry} />
          <StatPill label="Seniority" value={da.employment.seniority} />
          <StatPill label="Education" value={da.education} />
          <StatPill label="Household size" value={String(da.household.size)} />
          <StatPill label="Composition" value={da.household.composition} />
        </div>
        {da.household.monthly_income_inr && (
          <p className="text-sm text-parchment/70 mt-3 font-mono break-words">
            Monthly income: ₹{da.household.monthly_income_inr.toLocaleString("en-IN")}
          </p>
        )}
      </Section>

      {/* Footer */}
      <div className="mt-16 pt-6 border-t border-parchment/10 flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center min-h-[44px] font-mono text-sm text-parchment/70 active:text-parchment transition-colors"
        >
          ← Home
        </Link>
        <a
          href="mailto:mind@simulatte.io?subject=The%20Mind%20%E2%80%94%20feedback"
          className="inline-flex items-center min-h-[44px] font-mono text-sm text-parchment/70 active:text-signal transition-colors break-all"
        >
          mind@simulatte.io
        </a>
      </div>
    </main>
  );
}
