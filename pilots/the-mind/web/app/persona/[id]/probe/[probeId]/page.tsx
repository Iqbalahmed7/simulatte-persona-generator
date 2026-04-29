"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchProbe, ProbeResult } from "@/lib/api";
import ProbeResultCard from "@/components/ProbeResultCard";
import FeedbackModal from "@/components/FeedbackModal";

export default function ProbeResultPage() {
  const { id, probeId } = useParams<{ id: string; probeId: string }>();
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
        <Link href={`/persona/${id}`} className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Back to persona
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
      <div className="flex items-center justify-between mb-10 gap-3 flex-wrap">
        <Link href={`/persona/${id}/probe`} className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Test another product
        </Link>
        <div className="flex items-center gap-3">
          <a
            href={`/api/probes/${probeId}/download`}
            download
            className="border border-signal/60 text-parchment hover:border-signal hover:text-signal transition-colors px-3 py-1.5 font-mono uppercase tracking-widest text-[10px]"
          >
            Download JSON
          </a>
          <Link href={`/persona/${id}`} className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
            Back to {probe.persona_name.split(" ")[0]} →
          </Link>
        </div>
      </div>

      <ProbeResultCard probe={probe} personaId={id} isPublic={false} />
      <FeedbackModal surface="probe" />
    </main>
  );
}
