/**
 * /persona/[id]/layout.tsx — server-side wrapper that emits OG meta tags.
 *
 * The page itself is a client component, so it can't host generateMetadata.
 * This layout fetches the persona name/age/city and points LinkedIn /
 * Twitter / Slack at our /api/og/persona/[id] image.
 */
import type { Metadata } from "next";
import { fetchGeneratedPersona } from "@/lib/api";

interface Props {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}

export async function generateMetadata(
  { params }: { params: Promise<{ id: string }> },
): Promise<Metadata> {
  const { id } = await params;
  try {
    const p = await fetchGeneratedPersona(id);
    const da = p.demographic_anchor as {
      name?: string; age?: number; city?: string; country?: string;
      employment?: { occupation?: string };
    } | undefined;
    const di = (p as { derived_insights?: { decision_style?: string; primary_value_orientation?: string } }).derived_insights;
    const name = da?.name ?? "Persona";
    const place = [da?.city, da?.country].filter(Boolean).join(", ");
    const ageLine = [da?.age && `${da.age}`, place].filter(Boolean).join(" · ");
    const title = `${name} — Simulatte / The Mind`;
    // Pack 2-3 highlights into the description so platforms that show
    // text below the OG image (LinkedIn, WhatsApp) still surface depth.
    const tc = (s?: string) => s ? s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : "";
    const occ = tc(da?.employment?.occupation);
    const decides = tc(di?.decision_style);
    const values = tc(di?.primary_value_orientation);
    const bits = [ageLine, occ, decides && `decides ${decides.toLowerCase()}`, values && `values ${values.toLowerCase()}`].filter(Boolean);
    const desc = bits.length
      ? `${bits.join(" · ")}. Created with Simulatte / The Mind.`
      : "A behaviourally coherent synthetic person, created with Simulatte.";
    const ogUrl = `/api/og/persona/${id}`;
    return {
      title,
      description: desc,
      openGraph: {
        title, description: desc, type: "profile",
        images: [{ url: ogUrl, width: 1200, height: 630 }],
      },
      twitter: { card: "summary_large_image", title, description: desc, images: [ogUrl] },
    };
  } catch {
    return {
      title: "Persona — Simulatte / The Mind",
      description: "A behaviourally coherent synthetic person built by Simulatte.",
    };
  }
}

export default function PersonaLayout({ children }: Props) {
  return <>{children}</>;
}
