"use client";

/**
 * TwinCard.tsx — Card tile for a prospect Twin in the /operator grid.
 *
 * Mirrors PersonaGrid card aesthetics: border, hover state, footer meta row.
 * Includes a "…" context menu: Probe / Frame / Refresh / Enrich / Delete.
 */
import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type TwinCard as TwinCardType, deleteTwin } from "@/lib/operator-api";

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  const d = Math.floor(ms / 86400000);
  if (d === 0) return "today";
  if (d === 1) return "1d ago";
  if (d < 30) return `${d}d ago`;
  const mo = Math.floor(d / 30);
  return `${mo}mo ago`;
}

function ConfidenceChip({ level }: { level: "high" | "medium" | "low" }) {
  const styles = {
    high: "text-signal border-signal/30",
    medium: "text-parchment border-parchment/20",
    low: "text-static border-parchment/10",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border ${styles[level]}`}
    >
      {level === "low" && (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        </svg>
      )}
      {level}
    </span>
  );
}

function ContextMenu({
  twinId,
  onDelete,
}: {
  twinId: string;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close on outside click
  useState(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setConfirming(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  });

  async function handleDelete() {
    if (!confirming) { setConfirming(true); return; }
    setDeleting(true);
    try {
      await deleteTwin(twinId);
      onDelete();
    } catch {
      setDeleting(false);
      setConfirming(false);
    }
  }

  const menuItems = [
    { label: "Open probe", href: `/operator/${twinId}/probe` },
    { label: "Frame a draft", href: `/operator/${twinId}/frame` },
    { label: "Refresh twin", href: `/operator/${twinId}?refresh=1` },
    { label: "Enrich", href: `/operator/${twinId}/enrich` },
  ];

  return (
    <div ref={ref} className="relative" onClick={(e) => e.preventDefault()}>
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen((o) => !o); }}
        className="w-6 h-6 flex items-center justify-center text-static hover:text-parchment transition-colors"
        aria-label="Twin actions"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="5" cy="12" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="19" cy="12" r="2" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-44 bg-void border border-parchment/15 z-50 py-1 shadow-2xl">
          {menuItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="block px-3 py-2 text-xs font-mono text-parchment/70 hover:text-parchment hover:bg-parchment/[0.04] transition-colors"
              onClick={() => setOpen(false)}
            >
              {item.label}
            </Link>
          ))}
          <div className="border-t border-parchment/10 mt-1 pt-1">
            <button
              onClick={(e) => { e.stopPropagation(); handleDelete(); }}
              disabled={deleting}
              className={`block w-full text-left px-3 py-2 text-xs font-mono transition-colors ${
                confirming
                  ? "text-red-400 hover:bg-red-400/10"
                  : "text-static hover:text-parchment/70 hover:bg-parchment/[0.04]"
              }`}
            >
              {deleting ? "Deleting…" : confirming ? "Confirm delete?" : "Delete twin"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function TwinCard({
  twin,
  onDeleted,
}: {
  twin: TwinCardType;
  onDeleted: (twinId: string) => void;
}) {
  const refreshedText = timeAgo(twin.last_refreshed_at);
  const role = [twin.title, twin.company].filter(Boolean).join(" · ");

  return (
    <div className="group relative border border-parchment/10 hover:border-parchment/25 transition-colors">
      <Link href={`/operator/${twin.twin_id}`} className="block p-4 pr-10">
        {/* Stale indicator dot */}
        {twin.is_stale && (
          <span
            className="absolute top-3 right-10 w-1.5 h-1.5 rounded-full bg-red-400/60"
            title="Refresh recommended — last updated > 180 days ago"
          />
        )}

        {/* Name + role */}
        <div className="mb-2">
          <p className="text-parchment text-[17px] font-sans leading-tight truncate">
            {twin.full_name}
          </p>
          {role && (
            <p className="text-static text-[12px] font-mono truncate mt-0.5">{role}</p>
          )}
        </div>

        {/* Confidence */}
        <div className="mb-3">
          <ConfidenceChip level={twin.confidence} />
        </div>

        {/* Footer meta */}
        <div className="flex items-center gap-2 text-[10px] font-mono text-static flex-wrap">
          <span>{twin.probe_count} probe{twin.probe_count !== 1 ? "s" : ""}</span>
          {twin.last_frame_score !== null && (
            <>
              <span className="opacity-30">·</span>
              <span>last frame {twin.last_frame_score.toFixed(1)}</span>
            </>
          )}
          <span className="opacity-30">·</span>
          <span>refreshed {refreshedText}</span>
        </div>
      </Link>

      {/* Context menu — positioned absolute inside card */}
      <div className="absolute top-3 right-3">
        <ContextMenu twinId={twin.twin_id} onDelete={() => onDeleted(twin.twin_id)} />
      </div>
    </div>
  );
}
