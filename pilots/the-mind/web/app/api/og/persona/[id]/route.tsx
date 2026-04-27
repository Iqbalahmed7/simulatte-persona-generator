/**
 * GET /api/og/persona/[id] — 1200x630 OG image for a persona share.
 *
 * Pulled by LinkedIn / Twitter / WhatsApp when a persona URL is pasted.
 * Renders persona portrait + name + headline highlights (occupation,
 * location, decision style, primary value) + a "CREATED WITH SIMULATTE"
 * attribution stripe at the bottom.
 *
 * Cached at the CDN edge for 6h since persona data is immutable once generated.
 */
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const revalidate = 21600;

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

interface Persona {
  demographic_anchor?: {
    name?: string;
    age?: number;
    location?: { city?: string; country?: string };
    employment?: { occupation?: string; industry?: string };
  };
  derived_insights?: {
    decision_style?: string;
    primary_value_orientation?: string;
    trust_anchor?: string;
    risk_appetite?: string;
  };
  portrait_url?: string;
}

function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
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
  const di = p.derived_insights ?? {};
  const name = da.name ?? "Persona";

  // Subtitle: just the age (location now has its own highlight row)
  const ageLine = da.age ? `${da.age}` : "";

  // Up to 5 highlight rows
  const highlights: { label: string; value: string }[] = [];
  const place = [da.location?.city, da.location?.country].filter(Boolean).join(", ");
  if (place) highlights.push({ label: "LIVES IN", value: place.slice(0, 42) });
  const occ = da.employment?.occupation;
  if (occ) highlights.push({ label: "WORKS AS", value: titleCase(occ).slice(0, 42) });
  if (di.decision_style) {
    highlights.push({ label: "DECIDES", value: titleCase(di.decision_style).slice(0, 42) });
  }
  if (di.trust_anchor) {
    highlights.push({ label: "TRUSTS", value: titleCase(di.trust_anchor).slice(0, 42) });
  }
  if (di.primary_value_orientation) {
    highlights.push({ label: "VALUES", value: titleCase(di.primary_value_orientation).slice(0, 42) });
  }

  const portrait = p.portrait_url;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: "#050505",
          fontFamily: "Helvetica, Arial, sans-serif",
          color: "#E9E6DF",
        }}
      >
        {/* Main row: portrait + content */}
        <div style={{ display: "flex", flex: 1, padding: "56px 64px 0 64px" }}>
          {portrait && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={portrait}
              alt=""
              width={420}
              height={460}
              style={{
                width: 420, height: 460, objectFit: "cover",
                borderRadius: 4, marginRight: 48,
                border: "1px solid rgba(233,230,223,0.10)",
              }}
            />
          )}
          <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
            {/* Eyebrow */}
            <div style={{
              fontSize: 16, color: "#A8FF3E", letterSpacing: 4,
              textTransform: "uppercase", fontWeight: 700, marginBottom: 14,
            }}>
              The Mind · Simulatte
            </div>

            {/* Big name */}
            <div style={{
              fontSize: 76, fontWeight: 800, lineHeight: 0.96, marginBottom: 6,
              letterSpacing: "-0.02em",
            }}>
              {name}
            </div>

            {/* Age */}
            {ageLine && (
              <div style={{
                fontSize: 24, color: "rgba(233,230,223,0.55)", marginBottom: 22,
              }}>
                {ageLine}
              </div>
            )}

            {/* Highlight rows */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {highlights.map((h) => (
                <div key={h.label} style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
                  <div style={{
                    fontSize: 12, color: "rgba(233,230,223,0.45)",
                    letterSpacing: 2, textTransform: "uppercase",
                    fontWeight: 600, width: 88, flexShrink: 0,
                  }}>
                    {h.label}
                  </div>
                  <div style={{
                    fontSize: 20, color: "#E9E6DF", fontWeight: 500,
                  }}>
                    {h.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Attribution stripe */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "20px 64px",
          borderTop: "1px solid rgba(233,230,223,0.10)",
          marginTop: 32,
        }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 12,
            fontSize: 18, color: "rgba(233,230,223,0.85)",
            letterSpacing: 1, fontWeight: 600,
          }}>
            <div style={{
              width: 10, height: 10, background: "#A8FF3E", borderRadius: 999,
            }} />
            CREATED WITH SIMULATTE
          </div>
          <div style={{
            fontSize: 16, color: "rgba(233,230,223,0.50)",
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
