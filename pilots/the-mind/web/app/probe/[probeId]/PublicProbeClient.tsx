"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchProbe, ProbeResult } from "@/lib/api";
import ProbeResultCard from "@/components/ProbeResultCard";

export default function PublicProbeClient({ probeId }: { probeId: string }) {
  const [probe, setProbe] = useState<ProbeResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchProbe(probeId)
      .then(setProbe)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load probe")
      );
  }, [probeId]);

  if (error) {
    return (
      <main className="min-h-screen px-6 py-12 max-w-3xl mx-auto">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← The Mind
        </Link>
        <div className="mt-12 border border-parchment/10 p-6">
          <p className="font-mono text-sm text-static">{error}</p>
        </div>
      </main>
    );
  }

  if (!probe) {
    return (
      <main className="min-h-screen px-6 py-12 flex items-center justify-center">
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

  return (
    <main className="min-h-screen px-4 py-6 md:px-6 md:py-12 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-10">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← The Mind
        </Link>
        <Link
          href="/generate"
          className="inline-flex items-center gap-1.5 border border-signal text-signal font-condensed font-bold px-3 py-1.5 hover:bg-signal/10 transition-colors text-[11px] tracking-widest uppercase"
        >
          Generate your own persona →
        </Link>
      </div>

      <ProbeResultCard probe={probe} isPublic={true} />
    </main>
  );
}
