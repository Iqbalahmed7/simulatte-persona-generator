/**
 * GET /api/og/persona/[id] — 1200x630 OG image for a persona share.
 *
 * Pulled by LinkedIn / Twitter / Slack when a persona URL is pasted.
 * Renders persona portrait + name + age/city + Simulatte / The Mind branding.
 *
 * Cached at the CDN edge for 6h since persona data is immutable once generated.
 */
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const revalidate = 21600;

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

interface Persona {
  demographic_anchor?: { name?: string; age?: number; city?: string; country?: string };
  portrait_url?: string;
}

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  let p: Persona = {};
  try {
    const r = await fetch(`${API}/generated/${id}`, { cache: "force-cache" });
    if (r.ok) p = await r.json();
  } catch { /* render fallback below */ }

  const da = p.demographic_anchor ?? {};
  const name = da.name ?? "Persona";
  const sub = [da.age && `${da.age}`, da.city, da.country].filter(Boolean).join(" · ");
  const portrait = p.portrait_url;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#0a0a0a",
          fontFamily: "Helvetica, Arial, sans-serif",
          color: "#f0e6d2",
          padding: "64px",
        }}
      >
        {portrait && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={portrait}
            alt=""
            width={420}
            height={420}
            style={{ width: 420, height: 420, objectFit: "cover", borderRadius: 4, marginRight: 48 }}
          />
        )}
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", flex: 1 }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{
              fontSize: 18, color: "#A8FF3E", letterSpacing: 4,
              textTransform: "uppercase", fontWeight: 600, marginBottom: 16,
            }}>
              Simulatte / The Mind
            </div>
            <div style={{ fontSize: 96, fontWeight: 800, lineHeight: 1, marginBottom: 24 }}>
              {name}
            </div>
            {sub && (
              <div style={{ fontSize: 32, color: "rgba(240,230,210,0.7)" }}>{sub}</div>
            )}
          </div>
          <div style={{
            fontSize: 18, color: "rgba(240,230,210,0.5)",
            fontFamily: "monospace", letterSpacing: 2,
          }}>
            mind.simulatte.io
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
