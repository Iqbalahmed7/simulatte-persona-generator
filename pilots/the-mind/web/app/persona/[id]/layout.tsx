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
    const da = p.demographic_anchor as { name?: string; age?: number; city?: string; country?: string } | undefined;
    const name = da?.name ?? "Persona";
    const sub = [da?.age && `${da.age}`, da?.city, da?.country].filter(Boolean).join(" · ");
    const title = `${name} — Simulatte / The Mind`;
    const desc = sub
      ? `${sub}. A behaviourally coherent synthetic person built by Simulatte.`
      : "A behaviourally coherent synthetic person built by Simulatte.";
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
