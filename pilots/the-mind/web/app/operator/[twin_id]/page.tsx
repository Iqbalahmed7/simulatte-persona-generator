"use client";

/**
 * app/operator/[twin_id]/page.tsx — Twin detail view.
 *
 * 2-column layout (60/40 md, stacked sm):
 *   LEFT:  identity snapshot → decision architecture → trigger map →
 *          objection anticipator → message frame recs → call prep → gaps
 *   RIGHT: action card → stats card → disclaimer (sticky on md+)
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  getTwin,
  deleteTwin,
  streamRefresh,
  generateTwinPortrait,
  type TwinDetail,
  OperatorAllowanceError,
  OPERATOR_ERROR_MESSAGES,
  type BuildSSEEvent,
} from "@/lib/operator-api";
import { useOperatorAllowance } from "@/components/OperatorAllowanceProvider";

// ── Helpers ───────────────────────────────────────────────────────────────

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const d = Math.floor(ms / 86400000);
  if (d === 0) return "today";
  if (d === 1) return "1d ago";
  if (d < 30) return `${d}d ago`;
  return `${Math.floor(d / 30)}mo ago`;
}

// ── Shared primitives ─────────────────────────────────────────────────────

function SectionEyebrow({ label }: { label: string }) {
  return (
    <p className="text-[10px] font-sans font-semibold text-signal uppercase tracking-[0.18em] mb-3">
      {label}
    </p>
  );
}

function Divider() {
  return <div className="border-t border-parchment/8 my-6" />;
}

function ConfidenceChip({ level }: { level: "high" | "medium" | "low" }) {
  const styles = {
    high: "text-signal border-signal/30",
    medium: "text-parchment border-parchment/20",
    low: "text-static border-parchment/10",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border ${styles[level]}`}>
      {level === "low" && (
        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        </svg>
      )}
      {level} confidence
    </span>
  );
}

// ── Collapsible ───────────────────────────────────────────────────────────

function Collapsible({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-parchment/10">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-parchment/[0.02] transition-colors"
      >
        <span className="text-xs font-mono text-parchment/70 uppercase tracking-widest">{title}</span>
        <svg
          width="12" height="12" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          className={`text-static transition-transform ${open ? "rotate-180" : ""}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && <div className="px-4 pb-4 space-y-3">{children}</div>}
    </div>
  );
}

// ── Refresh progress mini-strip ───────────────────────────────────────────

function RefreshStrip({ message, error }: { message: string; error: string | null }) {
  return (
    <div className="flex items-center gap-2 text-xs font-mono mt-2">
      {error ? (
        <span className="text-red-400">{error}</span>
      ) : (
        <>
          <span className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse flex-shrink-0" />
          <span className="text-static truncate">{message}</span>
        </>
      )}
    </div>
  );
}

// ── LEFT COLUMN sections ──────────────────────────────────────────────────

function IdentitySnapshot({ text }: { text: string }) {
  return (
    <div>
      <SectionEyebrow label="Identity snapshot" />
      <p className="text-parchment/85 text-[15px] leading-relaxed">{text}</p>
    </div>
  );
}

function DecisionArchitecture({ da }: { da: TwinDetail["decision_architecture"] }) {
  const rows: Array<{ key: keyof typeof da; label: string }> = [
    { key: "first_filter", label: "First filter" },
    { key: "trust_signal", label: "Trust signal" },
    { key: "rejection_trigger", label: "Rejection trigger" },
    { key: "engagement_threshold", label: "Engagement threshold" },
  ];
  return (
    <div>
      <SectionEyebrow label="Decision architecture" />
      <div className="space-y-3">
        {rows.map(({ key, label }) => (
          <div key={key} className="grid grid-cols-[140px_1fr] gap-3 items-start">
            <p className="text-[11px] font-mono text-static uppercase tracking-widest pt-0.5">{label}</p>
            <p className="text-parchment/80 text-[14px] leading-snug">{da[key]}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function TriggerMap({ tm }: { tm: TwinDetail["trigger_map"] }) {
  return (
    <div>
      <SectionEyebrow label="Trigger map" />
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-[10px] font-mono text-parchment/40 uppercase tracking-widest mb-2">Leans in</p>
          <ul className="space-y-1.5">
            {tm.leans_in.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-parchment/80 leading-snug">
                <span className="w-1.5 h-1.5 rounded-full bg-signal mt-1.5 flex-shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-[10px] font-mono text-parchment/40 uppercase tracking-widest mb-2">Disengages</p>
          <ul className="space-y-1.5">
            {tm.disengages.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-static leading-snug">
                <span className="w-1.5 h-1.5 rounded-full bg-static/40 mt-1.5 flex-shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function ObjPair({ pair }: { pair: TwinDetail["objection_anticipator"]["first_contact"][number] }) {
  return (
    <div className="border-l-2 border-parchment/10 pl-3 space-y-1">
      <p className="text-[12px] font-mono text-parchment/60 italic">{pair.objection}</p>
      <p className="text-[13px] text-parchment/80 leading-snug">
        <span className="text-static text-[10px] font-mono uppercase tracking-widest mr-1.5">Preempt</span>
        {pair.preempt}
      </p>
      <p className="text-[13px] text-parchment/60 leading-snug">
        <span className="text-static text-[10px] font-mono uppercase tracking-widest mr-1.5">Response</span>
        {pair.response}
      </p>
    </div>
  );
}

function ObjectionAnticipator({ oa }: { oa: TwinDetail["objection_anticipator"] }) {
  return (
    <div>
      <SectionEyebrow label="Objection anticipator" />
      <div className="space-y-2">
        <Collapsible title="First contact">
          {oa.first_contact.map((p, i) => <ObjPair key={i} pair={p} />)}
        </Collapsible>
        <Collapsible title="First call">
          {oa.first_call.map((p, i) => <ObjPair key={i} pair={p} />)}
        </Collapsible>
      </div>
    </div>
  );
}

function MessageFrameRecs({ mfr }: { mfr: TwinDetail["message_frame_recommendations"] }) {
  const rows: Array<{ key: keyof typeof mfr; label: string }> = [
    { key: "lead_with", label: "Lead with" },
    { key: "avoid", label: "Avoid" },
    { key: "tone", label: "Tone" },
    { key: "format", label: "Format" },
    { key: "timing", label: "Timing" },
  ];
  return (
    <div>
      <SectionEyebrow label="Message frame recommendations" />
      <div className="space-y-3">
        {rows.map(({ key, label }) => (
          <div key={key} className="grid grid-cols-[100px_1fr] gap-3 items-start">
            <p className="text-[11px] font-mono text-static uppercase tracking-widest pt-0.5">{label}</p>
            <p className="text-parchment/80 text-[14px] leading-snug">{mfr[key]}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CallPrep({ cp }: { cp: TwinDetail["call_prep"] }) {
  return (
    <div>
      <SectionEyebrow label="Call prep" />
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-[10px] font-mono text-parchment/40 uppercase tracking-widest mb-2">Have ready</p>
          <ul className="space-y-1.5">
            {cp.have_ready.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-parchment/80 leading-snug">
                <span className="text-signal mt-0.5 flex-shrink-0">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-[10px] font-mono text-parchment/40 uppercase tracking-widest mb-2">Do not say</p>
          <ul className="space-y-1.5">
            {cp.do_not_say.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-static leading-snug">
                <span className="text-red-400/60 mt-0.5 flex-shrink-0">✗</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Gaps({ gaps }: { gaps: string[] }) {
  if (!gaps.length) return null;
  return (
    <div className="bg-parchment/[0.02] border border-parchment/8 p-4">
      <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-2">Gaps — what we couldn't find</p>
      <ul className="space-y-1">
        {gaps.map((g, i) => (
          <li key={i} className="text-[12px] font-mono text-static/70">{g}</li>
        ))}
      </ul>
    </div>
  );
}

// ── RIGHT COLUMN ──────────────────────────────────────────────────────────

function PortraitCard({
  twinId,
  initialUrl,
}: {
  twinId: string;
  initialUrl: string | null;
}) {
  const [url, setUrl] = useState<string | null>(initialUrl);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate(force = false) {
    setGenerating(true);
    setError(null);
    try {
      const newUrl = await generateTwinPortrait(twinId, force);
      setUrl(newUrl);
    } catch (err) {
      setError((err as Error).message ?? "Portrait generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="border border-parchment/10 overflow-hidden">
      {url ? (
        <>
          <div className="relative w-full aspect-[3/4]">
            <Image
              src={url}
              alt="Twin portrait"
              fill
              sizes="256px"
              className="object-cover"
              unoptimized
            />
          </div>
          <div className="p-2 flex justify-between items-center border-t border-parchment/10">
            <p className="text-[10px] font-mono text-static">
              AI-generated · not the person
            </p>
            <button
              onClick={() => handleGenerate(true)}
              disabled={generating}
              className="text-[10px] font-mono text-static hover:text-parchment/60 transition-colors disabled:opacity-40"
            >
              {generating ? "…" : "↻"}
            </button>
          </div>
        </>
      ) : (
        <div className="p-4 space-y-3">
          <p className="text-[10px] font-mono text-static uppercase tracking-widest">Portrait</p>
          <div className="w-full aspect-[3/4] bg-parchment/[0.03] flex items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="1" className="text-parchment/10" strokeLinecap="round">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
            </svg>
          </div>
          {error && <p className="text-red-400 text-[11px] font-mono">{error}</p>}
          <button
            onClick={() => handleGenerate(false)}
            disabled={generating}
            className="w-full py-2 border border-parchment/15 hover:border-parchment/30 text-parchment/50 hover:text-parchment/80 text-xs font-mono transition-colors disabled:opacity-40"
          >
            {generating ? (
              <span className="flex items-center justify-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-signal animate-pulse" />
                Generating…
              </span>
            ) : (
              "Generate portrait"
            )}
          </button>
          <p className="text-[10px] font-mono text-parchment/20 leading-relaxed">
            AI-generated likeness. Not the actual person.
          </p>
        </div>
      )}
    </div>
  );
}

function ActionCard({
  twinId,
  isDeleting,
  onDelete,
}: {
  twinId: string;
  isDeleting: boolean;
  onDelete: () => void;
}) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const actions = [
    { label: "Open probe", href: `/operator/${twinId}/probe`, primary: true },
    { label: "Frame a draft", href: `/operator/${twinId}/frame` },
    { label: "Enrich with new signal", href: `/operator/${twinId}/enrich` },
  ];

  return (
    <div className="border border-parchment/10 p-4 space-y-2">
      <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">Actions</p>
      {actions.map((a) => (
        <Link
          key={a.label}
          href={a.href}
          className={`block w-full text-center py-2.5 text-sm font-mono transition-colors border ${
            a.primary
              ? "bg-signal/10 hover:bg-signal/20 border-signal/30 text-signal"
              : "border-parchment/15 hover:border-parchment/30 text-parchment/70 hover:text-parchment"
          }`}
        >
          {a.label}
        </Link>
      ))}
      <button
        onClick={() => {
          if (!confirmDelete) { setConfirmDelete(true); return; }
          onDelete();
        }}
        disabled={isDeleting}
        className={`w-full py-2.5 text-sm font-mono transition-colors border ${
          confirmDelete
            ? "border-red-400/30 text-red-400 hover:bg-red-400/10"
            : "border-parchment/10 text-static hover:text-parchment/50"
        }`}
      >
        {isDeleting ? "Deleting…" : confirmDelete ? "Confirm delete?" : "Delete twin"}
      </button>
    </div>
  );
}

function StatsCard({
  twin,
  refreshing,
  refreshMessage,
  refreshError,
  onRefresh,
}: {
  twin: TwinDetail;
  refreshing: boolean;
  refreshMessage: string;
  refreshError: string | null;
  onRefresh: () => void;
}) {
  const stats = [
    { label: "Probes run", value: String(twin.probe_count) },
    { label: "Last frame score", value: twin.last_frame_score !== null ? twin.last_frame_score.toFixed(1) : "—" },
    { label: "Recon sources", value: String(twin.recon_source_count) },
    { label: "Last refreshed", value: timeAgo(twin.last_refreshed_at) },
  ];
  return (
    <div className="border border-parchment/10 p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-mono text-static uppercase tracking-widest">Stats</p>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="text-[10px] font-mono text-static hover:text-parchment/60 transition-colors disabled:opacity-40"
        >
          {refreshing ? "Refreshing…" : twin.is_stale ? "↻ Refresh (stale)" : "↻ Refresh"}
        </button>
      </div>
      <div className="space-y-2">
        {stats.map((s) => (
          <div key={s.label} className="flex justify-between items-baseline">
            <p className="text-[11px] font-mono text-static">{s.label}</p>
            <p className={`text-[13px] font-mono ${
              s.label === "Last frame score" && twin.last_frame_score !== null
                ? twin.last_frame_score >= 8.5 ? "text-signal" : "text-parchment/70"
                : "text-parchment/70"
            }`}>{s.value}</p>
          </div>
        ))}
      </div>
      {(refreshing || refreshError) && (
        <RefreshStrip message={refreshMessage} error={refreshError} />
      )}
    </div>
  );
}

function Disclaimer() {
  return (
    <p className="text-[11px] font-mono text-parchment/20 leading-relaxed">
      This is a probabilistic decision-filter model built from public signal.
      Not the person — a structured approximation for pre-call prep only.
    </p>
  );
}

// ── Page skeleton ─────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="min-h-screen bg-void px-4 md:px-8 py-8 max-w-6xl mx-auto animate-pulse">
      <div className="h-4 bg-parchment/8 w-24 mb-6" />
      <div className="flex gap-8">
        <div className="flex-1 space-y-6">
          <div className="h-8 bg-parchment/8 w-1/2" />
          <div className="h-4 bg-parchment/5 w-full" />
          <div className="h-4 bg-parchment/5 w-5/6" />
          <div className="h-4 bg-parchment/5 w-4/6" />
        </div>
        <div className="w-64 flex-shrink-0 space-y-3">
          <div className="h-32 bg-parchment/5" />
          <div className="h-24 bg-parchment/5" />
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function TwinDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const twinId = params.twin_id as string;
  const { triggerOperatorAllowanceExceeded } = useOperatorAllowance();

  const [twin, setTwin] = useState<TwinDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  // Refresh state
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState("");
  const [refreshError, setRefreshError] = useState<string | null>(null);

  // Delete state
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getTwin(twinId);
      setTwin(data);
    } catch (err) {
      setPageError((err as Error).message ?? "Failed to load Twin");
    } finally {
      setLoading(false);
    }
  }, [twinId]);

  useEffect(() => { load(); }, [load]);

  // Auto-trigger refresh if ?refresh=1
  useEffect(() => {
    if (searchParams.get("refresh") === "1" && twin && !refreshing) {
      handleRefresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [twin]);

  async function handleRefresh() {
    if (refreshing) return;
    setRefreshing(true);
    setRefreshError(null);
    setRefreshMessage("Starting refresh…");
    try {
      await streamRefresh(twinId, (evt: BuildSSEEvent) => {
        if (evt.stage === "recon") setRefreshMessage(evt.message ?? "Searching public sources…");
        else if (evt.stage === "synthesis") setRefreshMessage(evt.message ?? "Re-synthesising…");
        else if (evt.stage === "ready") {
          setRefreshMessage("Done");
          load(); // re-fetch updated twin
        } else if (evt.stage === "error") {
          const code = evt.error_code ?? "";
          setRefreshError(OPERATOR_ERROR_MESSAGES[code] ?? evt.error ?? "Refresh failed.");
        }
      });
    } catch (err) {
      if (err instanceof OperatorAllowanceError) {
        triggerOperatorAllowanceExceeded(err.payload);
      } else {
        setRefreshError((err as Error).message ?? "Refresh failed.");
      }
    } finally {
      setRefreshing(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteTwin(twinId);
      router.push("/operator");
    } catch (err) {
      setDeleting(false);
      setPageError((err as Error).message ?? "Delete failed.");
    }
  }

  if (loading) return <PageSkeleton />;

  if (pageError || !twin) {
    return (
      <div className="min-h-screen bg-void px-4 py-8 max-w-6xl mx-auto">
        <Link href="/operator" className="text-[11px] font-mono text-static hover:text-parchment/60 mb-6 inline-block">
          ← Back to Twins
        </Link>
        <p className="text-red-400 text-sm font-mono">{pageError ?? "Twin not found."}</p>
      </div>
    );
  }

  const role = [twin.title, twin.company].filter(Boolean).join(" · ");

  return (
    <div className="min-h-screen bg-void px-4 md:px-8 py-8 max-w-6xl mx-auto">
      {/* Back */}
      <Link
        href="/operator"
        className="inline-flex items-center gap-1.5 text-[11px] font-mono text-static hover:text-parchment/60 transition-colors mb-6"
      >
        ← Twins
      </Link>

      {/* 2-col layout */}
      <div className="flex flex-col md:flex-row gap-8">

        {/* ── LEFT (60%) ── */}
        <div className="flex-1 min-w-0 space-y-0">

          {/* Header */}
          <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
            <div>
              <h1 className="font-condensed font-black text-parchment text-3xl uppercase tracking-wide leading-none">
                {twin.full_name}
              </h1>
              {role && (
                <p className="text-static text-[13px] font-mono mt-1">{role}</p>
              )}
              <div className="mt-2">
                <ConfidenceChip level={twin.confidence} />
              </div>
            </div>
            <div className="flex gap-2">
              <Link
                href={`/operator/${twinId}/enrich`}
                className="px-3 py-1.5 border border-parchment/15 hover:border-parchment/30 text-parchment/60 hover:text-parchment text-xs font-mono transition-colors"
              >
                Enrich
              </Link>
            </div>
          </div>

          <IdentitySnapshot text={twin.identity_snapshot} />
          <Divider />
          <DecisionArchitecture da={twin.decision_architecture} />
          <Divider />
          <TriggerMap tm={twin.trigger_map} />
          <Divider />
          <ObjectionAnticipator oa={twin.objection_anticipator} />
          <Divider />
          <MessageFrameRecs mfr={twin.message_frame_recommendations} />
          <Divider />
          <CallPrep cp={twin.call_prep} />
          <Divider />
          <Gaps gaps={twin.gaps} />
        </div>

        {/* ── RIGHT (40%) — sticky on md ── */}
        <div className="w-full md:w-64 flex-shrink-0 space-y-4 md:sticky md:top-8 md:self-start">
          <PortraitCard twinId={twinId} initialUrl={twin.portrait_url} />
          <ActionCard twinId={twinId} isDeleting={deleting} onDelete={handleDelete} />
          <StatsCard
            twin={twin}
            refreshing={refreshing}
            refreshMessage={refreshMessage}
            refreshError={refreshError}
            onRefresh={handleRefresh}
          />
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}
