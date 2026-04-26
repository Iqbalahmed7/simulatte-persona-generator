import { Metadata } from "next";
import { fetchProbe, API } from "@/lib/api";
import PublicProbeClient from "./PublicProbeClient";

interface Props {
  params: { probeId: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const probe = await fetchProbe(params.probeId);
    const rationale = probe.purchase_intent.rationale.slice(0, 100);
    const ogImageUrl = `${API}/probes/${params.probeId}/og`;
    return {
      title: `${probe.persona_name} on ${probe.product_name} — Simulatte`,
      description: `Purchase intent ${probe.purchase_intent.score}/10 — "${rationale}"`,
      openGraph: {
        title: `${probe.persona_name} on ${probe.product_name} — Simulatte`,
        description: `Purchase intent ${probe.purchase_intent.score}/10 — "${rationale}"`,
        images: [{ url: ogImageUrl, width: 1200, height: 630 }],
        type: "website",
      },
      twitter: {
        card: "summary_large_image",
        title: `${probe.persona_name} on ${probe.product_name} — Simulatte`,
        description: `Purchase intent ${probe.purchase_intent.score}/10 — "${rationale}"`,
        images: [ogImageUrl],
      },
    };
  } catch {
    return {
      title: "Litmus Probe — Simulatte",
      description: "Structured product evaluation by a synthetic persona.",
    };
  }
}

export default function PublicProbePage({ params }: Props) {
  return <PublicProbeClient probeId={params.probeId} />;
}
