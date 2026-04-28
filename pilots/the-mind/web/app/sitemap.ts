/**
 * /sitemap.xml — generated at build time.
 *
 * Lists static pages plus the public persona share pages so search
 * engines can index the OG cards. Persona IDs are pulled at build
 * time from the API; if the API is unreachable we still emit a valid
 * sitemap with just the static pages.
 */
import type { MetadataRoute } from "next";

const SITE = "https://mind.simulatte.io";
const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

interface PublicPersona { persona_id: string; }

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE}/`,           lastModified: now, priority: 1.0, changeFrequency: "weekly" },
    { url: `${SITE}/community`,  lastModified: now, priority: 0.8, changeFrequency: "daily"  },
    { url: `${SITE}/privacy`,    lastModified: now, priority: 0.3, changeFrequency: "yearly" },
    { url: `${SITE}/terms`,      lastModified: now, priority: 0.3, changeFrequency: "yearly" },
  ];

  // Public personas — best-effort fetch, fail-soft so deploy never blocks.
  let personaUrls: MetadataRoute.Sitemap = [];
  try {
    const r = await fetch(`${API}/generated`, {
      next: { revalidate: 3600 }, // refresh hourly
    });
    if (r.ok) {
      const list = (await r.json()) as PublicPersona[];
      personaUrls = list.slice(0, 1000).map((p) => ({
        url: `${SITE}/persona/${p.persona_id}`,
        lastModified: now,
        priority: 0.6,
        changeFrequency: "monthly" as const,
      }));
    }
  } catch { /* keep empty */ }

  return [...staticPages, ...personaUrls];
}
