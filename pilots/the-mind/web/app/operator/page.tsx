"use client";

/**
 * app/operator/page.tsx — Twin grid. List view of all prospect Twins.
 *
 * /operator — requires auth (AccessGate handles it via AppShell).
 * Feature flag enforced by app/operator/layout.tsx.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import TwinCard from "@/components/TwinCard";
import { listTwins, type TwinCard as TwinCardType } from "@/lib/operator-api";

function Skeleton() {
  return (
    <div className="border border-parchment/8 p-4 animate-pulse space-y-3">
      <div className="h-4 bg-parchment/8 w-2/3" />
      <div className="h-3 bg-parchment/5 w-1/2" />
      <div className="h-5 bg-parchment/5 w-16 mt-2" />
      <div className="h-3 bg-parchment/5 w-full mt-3" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="col-span-full py-24 flex flex-col items-center gap-5 text-center">
      {/* Crosshair illustration */}
      <svg
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
        className="text-parchment/15"
        strokeLinecap="round"
      >
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="4" />
        <line x1="12" y1="3" x2="12" y2="7" />
        <line x1="12" y1="17" x2="12" y2="21" />
        <line x1="3" y1="12" x2="7" y2="12" />
        <line x1="17" y1="12" x2="21" y2="12" />
      </svg>
      <div className="space-y-1">
        <p className="text-parchment font-condensed font-bold text-lg uppercase tracking-wide">
          No Twins yet
        </p>
        <p className="text-static text-sm font-mono max-w-xs">
          Build your first prospect Twin to start simulating conversations.
        </p>
      </div>
      <Link
        href="/operator/build"
        className="mt-2 px-5 py-2.5 bg-signal/10 hover:bg-signal/20 border border-signal/30 text-signal text-sm font-mono transition-colors"
      >
        Build a Twin →
      </Link>
    </div>
  );
}

export default function OperatorPage() {
  const [twins, setTwins] = useState<TwinCardType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTwins()
      .then((data) => { setTwins(data); setLoading(false); })
      .catch((err) => { setError(err.message ?? "Failed to load Twins"); setLoading(false); });
  }, []);

  function handleDeleted(twinId: string) {
    setTwins((prev) => prev.filter((t) => t.twin_id !== twinId));
  }

  return (
    <div className="min-h-screen bg-void px-4 md:px-8 py-8 max-w-6xl mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <p className="text-[10px] font-mono text-signal uppercase tracking-[0.18em] mb-1">
            The Operator
          </p>
          <h1 className="font-condensed font-black text-parchment text-3xl uppercase tracking-wide">
            Twins
          </h1>
          <p className="text-static text-sm font-mono mt-1">
            Prospect decision-filter models built from public signal.
          </p>
        </div>
        <Link
          href="/operator/build"
          className="flex-shrink-0 px-4 py-2.5 bg-signal/10 hover:bg-signal/20 border border-signal/30 text-signal text-sm font-mono transition-colors whitespace-nowrap"
        >
          + Build a Twin
        </Link>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 border border-red-400/20 bg-red-400/5 p-4">
          <p className="text-red-400 text-sm font-mono">{error}</p>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)
        ) : twins.length === 0 ? (
          <EmptyState />
        ) : (
          twins.map((twin) => (
            <TwinCard key={twin.twin_id} twin={twin} onDeleted={handleDeleted} />
          ))
        )}
      </div>
    </div>
  );
}
