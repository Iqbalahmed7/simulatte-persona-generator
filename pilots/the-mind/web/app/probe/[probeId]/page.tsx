import { Metadata } from "next";
import { fetchProbe } from "@/lib/api";
import PublicProbeClient from "./PublicProbeClient";

interface Props {
  params: Promise<{ probeId: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { probeId } = await params;
  try {
    const probe = await fetchProbe(probeId);
    const rationale = probe.purchase_intent.rationale.slice(0, 100);
    const ogImageUrl = `/api/og/probe/${probeId}`;
    const title = `${probe.persona_name} on ${probe.product_name} — Simulatte`;
    const desc = `Purchase intent ${probe.purchase_intent.score}/10 — "${rationale}"`;
    return {
      title,
      description: desc,
      openGraph: {
        title, description: desc, type: "website",
        images: [{ url: ogImageUrl, width: 1200, height: 630 }],
      },
      twitter: { card: "summary_large_image", title, description: desc, images: [ogImageUrl] },
    };
  } catch {
    return {
      title: "Litmus Probe — Simulatte",
      description: "Structured product evaluation by a synthetic persona.",
    };
  }
}

export default async function PublicProbePage({ params }: Props) {
  const { probeId } = await params;
  return <PublicProbeClient probeId={probeId} />;
}
