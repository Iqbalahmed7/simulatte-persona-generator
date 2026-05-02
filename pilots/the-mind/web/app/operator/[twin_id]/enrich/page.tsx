"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getTwin,
  enrichTwinWithText,
  enrichTwinWithUrl,
  enrichTwinWithPdf,
  type TwinDetail,
} from "@/lib/operator-api";

// ── Icons ──────────────────────────────────────────────────────────────────

function chevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Signal hints ───────────────────────────────────────────────────────────

const SIGNAL_HINTS = [
  "A recent LinkedIn post or article they wrote",
  "Notes from a previous call or meeting",
  "Company press release or earnings commentary",
  "Podcast or conference transcript excerpt",
  "Email thread or reply they sent you",
  "Peer or colleague description of how they operate",
  "CRM notes from a past deal or interaction",
];

type Tab = "text" | "url" | "pdf";

// ── Main page ──────────────────────────────────────────────────────────────

export default function EnrichPage() {
  const params = useParams<{ twin_id: string }>();
  const twinId = params.twin_id;
  const router = useRouter();

  const [twin, setTwin] = useState<TwinDetail | null>(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  const [tab, setTab] = useState<Tab>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getTwin(twinId)
      .then(setTwin)
      .catch(() => setPageError("Failed to load Twin."))
      .finally(() => setPageLoading(false));
  }, [twinId]);

  function handleTextChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 480)}px`;
    }
  }

  function canSubmit(): boolean {
    if (submitting) return false;
    if (tab === "text") return text.trim().length >= 10;
    if (tab === "url") return /^https?:\/\/.+/i.test(url.trim());
    if (tab === "pdf") return pdfFile !== null;
    return false;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit()) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      if (tab === "text") {
        await enrichTwinWithText(twinId, text.trim());
      } else if (tab === "url") {
        await enrichTwinWithUrl(twinId, url.trim());
      } else if (tab === "pdf" && pdfFile) {
        await enrichTwinWithPdf(twinId, pdfFile);
      }
      setDone(true);
      setTimeout(() => router.push(`/operator/${twinId}`), 1200);
    } catch (err) {
      setSubmitError((err as Error).message ?? "Enrichment failed.");
      setSubmitting(false);
    }
  }

  if (pageLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-static text-xs font-mono animate-pulse">Loading…</span>
      </div>
    );
  }

  if (pageError || !twin) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-static text-sm">{pageError ?? "Twin not found."}</p>
          <Link href="/operator" className="text-parchment text-sm underline">
            ← Back to Twins
          </Link>
        </div>
      </div>
    );
  }

  const twinName = twin.full_name;
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  const tabBtn = (id: Tab, label: string) => (
    <button
      type="button"
      onClick={() => {
        setTab(id);
        setSubmitError(null);
      }}
      disabled={submitting || done}
      className={`px-4 py-2 text-xs font-mono uppercase tracking-wider border transition-colors ${
        tab === id
          ? "border-parchment text-parchment bg-white/5"
          : "border-white/10 text-static hover:text-parchment hover:border-white/20"
      } disabled:opacity-50`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-3 px-6 py-3 border-b border-white/8">
        <Link
          href={`/operator/${twinId}`}
          className="text-static hover:text-parchment transition-colors"
        >
          {chevronLeft()}
        </Link>
        <div>
          <span className="text-parchment text-sm font-semibold">{twinName}</span>
          <span className="text-static text-xs font-mono ml-2">/ Enrich</span>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8 space-y-8">

          {/* Intro */}
          <div className="space-y-2">
            <p className="text-static text-[10px] font-mono uppercase tracking-wider">
              Add new intelligence
            </p>
            <h1 className="text-parchment text-xl font-semibold leading-snug">
              Enrich {twinName}&#39;s Twin
            </h1>
            <p className="text-static text-sm leading-relaxed">
              Add a URL, upload a PDF, or paste text that reveals how {twinName} thinks,
              decides, or communicates. The Twin is re-synthesised on top of existing
              recon — nothing is overwritten.
            </p>
          </div>

          {/* Signal hints */}
          <div className="border border-white/8 bg-white/2 px-4 py-4 space-y-2">
            <p className="text-static text-[10px] font-mono uppercase tracking-wider mb-3">
              What works well
            </p>
            <ul className="space-y-1.5">
              {SIGNAL_HINTS.map((hint) => (
                <li key={hint} className="flex items-start gap-2 text-sm text-static">
                  <span className="mt-1.5 w-1 h-1 rounded-full bg-static/40 shrink-0" />
                  {hint}
                </li>
              ))}
            </ul>
          </div>

          {/* Tabs */}
          <div className="flex gap-2">
            {tabBtn("text", "Text")}
            {tabBtn("url", "URL")}
            {tabBtn("pdf", "PDF")}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {tab === "text" && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-static text-[10px] font-mono uppercase tracking-wider">
                    Signal text
                  </label>
                  <span className="text-static text-[10px] font-mono">
                    {wordCount > 0 ? `${wordCount} words` : ""}
                  </span>
                </div>
                <textarea
                  ref={textareaRef}
                  value={text}
                  onChange={handleTextChange}
                  placeholder={`Paste text here — a LinkedIn post, call notes, article excerpt, or anything that reveals how ${twinName} operates…`}
                  disabled={submitting || done}
                  rows={10}
                  className="w-full resize-none bg-white/4 border border-white/10 text-parchment text-sm placeholder:text-static/40 px-4 py-3 focus:outline-none focus:border-white/20 disabled:opacity-50 transition-colors leading-relaxed"
                  style={{ minHeight: 200 }}
                />
              </div>
            )}

            {tab === "url" && (
              <div className="space-y-2">
                <label className="text-static text-[10px] font-mono uppercase tracking-wider">
                  Public URL
                </label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=... or https://blog.example.com/..."
                  disabled={submitting || done}
                  className="w-full bg-white/4 border border-white/10 text-parchment text-sm placeholder:text-static/40 px-4 py-3 focus:outline-none focus:border-white/20 disabled:opacity-50 transition-colors"
                />
                <p className="text-static text-[10px] font-mono leading-relaxed pt-1">
                  Article, blog post, press release, public profile, or YouTube video
                  (transcript fetched automatically). Login-walled and JS-rendered
                  pages won&#39;t fetch.
                </p>
              </div>
            )}

            {tab === "pdf" && (
              <div className="space-y-2">
                <label className="text-static text-[10px] font-mono uppercase tracking-wider">
                  PDF document
                </label>
                <div className="border border-dashed border-white/15 px-4 py-6 bg-white/2">
                  <input
                    type="file"
                    accept="application/pdf,.pdf"
                    onChange={(e) => setPdfFile(e.target.files?.[0] ?? null)}
                    disabled={submitting || done}
                    className="block w-full text-sm text-static file:mr-4 file:py-2 file:px-4 file:border-0 file:bg-parchment file:text-void file:text-xs file:font-mono file:uppercase file:tracking-wider file:cursor-pointer hover:file:bg-parchment/80 disabled:opacity-50"
                  />
                  {pdfFile && (
                    <p className="text-parchment text-xs font-mono mt-3">
                      {pdfFile.name} <span className="text-static">· {(pdfFile.size / 1024).toFixed(0)} KB</span>
                    </p>
                  )}
                </div>
                <p className="text-static text-[10px] font-mono leading-relaxed pt-1">
                  LinkedIn export, deck, transcript, report. Max 8 MB.
                  Scanned image-only PDFs won&#39;t parse.
                </p>
              </div>
            )}

            {submitError && (
              <p className="text-red-400 text-xs font-mono">{submitError}</p>
            )}

            <div className="flex items-center justify-between pt-1">
              <p className="text-static text-[10px] font-mono max-w-xs leading-relaxed">
                Enrichment re-runs synthesis. The Twin profile will update
                within a few seconds.
              </p>

              {done ? (
                <div className="flex items-center gap-2 text-signal text-sm font-mono">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M2 7l4 4 6-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Enriched — redirecting…
                </div>
              ) : (
                <button
                  type="submit"
                  disabled={!canSubmit()}
                  className="text-sm font-mono text-void bg-parchment px-5 py-2.5 hover:bg-parchment/80 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  {submitting ? (
                    <span className="animate-pulse">Enriching…</span>
                  ) : (
                    "Enrich Twin"
                  )}
                </button>
              )}
            </div>
          </form>

          {/* Current gaps callout */}
          {twin.gaps && twin.gaps.length > 0 && (
            <div className="border border-white/8 bg-white/2 px-4 py-4 space-y-2">
              <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                Known gaps in this Twin
              </p>
              <ul className="space-y-1.5">
                {twin.gaps.map((gap, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-static">
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-amber-400/50 shrink-0" />
                    {gap}
                  </li>
                ))}
              </ul>
              <p className="text-static text-[10px] font-mono pt-1">
                Enriching with targeted signal can close these gaps.
              </p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
