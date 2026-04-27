/**
 * GET /api/og/probe/[id] — 1200x630 OG image for a probe verdict share.
 *
 * Renders persona portrait + product name + intent score + top objection.
 * Pulled by LinkedIn / Twitter / Slack when a probe URL is pasted.
 */
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const revalidate = 21600;

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

interface Probe {
  product_name?: string;
  category?: string;
  persona_name?: string;
  persona_portrait_url?: string | null;
  purchase_intent?: { score?: number };
  top_objection?: string;
}

function intentColor(score: number | undefined): string {
  if (score === undefined) return "#9A9997";
  if (score >= 7) return "#A8FF3E"; // signal green
  if (score >= 4) return "#E9E6DF"; // parchment
  return "#9A9997"; // static — never red
}

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  let p: Probe = {};
  try {
    const r = await fetch(`${API}/probes/${id}`, { cache: "force-cache" });
    if (r.ok) p = await r.json();
  } catch { /* render fallback below */ }

  const product = p.product_name ?? "Product";
  const personaName = p.persona_name ?? "Persona";
  const score = p.purchase_intent?.score;
  const objection = (p.top_objection ?? "").slice(0, 220);
  const portrait = p.persona_portrait_url;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: "#0a0a0a",
          fontFamily: "Helvetica, Arial, sans-serif",
          color: "#f0e6d2",
          padding: "56px 64px",
        }}
      >
        <div style={{
          fontSize: 18, color: "#A8FF3E", letterSpacing: 4,
          textTransform: "uppercase", fontWeight: 600, marginBottom: 16,
        }}>
          Simulatte / Litmus probe
        </div>
        <div style={{ display: "flex", flex: 1, gap: 36, alignItems: "center" }}>
          {portrait && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={portrait}
              alt=""
              width={300}
              height={300}
              style={{ width: 300, height: 300, objectFit: "cover", borderRadius: 4, flexShrink: 0 }}
            />
          )}
          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            <div style={{ fontSize: 22, color: "rgba(240,230,210,0.7)", marginBottom: 8 }}>
              {personaName} on
            </div>
            <div style={{ fontSize: 64, fontWeight: 800, lineHeight: 1.05, marginBottom: 28 }}>
              {product}
            </div>
            {score !== undefined && (
              <div style={{ display: "flex", alignItems: "baseline", marginBottom: 24 }}>
                <span style={{
                  fontSize: 96, fontWeight: 800, color: intentColor(score), lineHeight: 1,
                }}>
                  {score}
                </span>
                <span style={{ fontSize: 28, color: "rgba(240,230,210,0.5)", marginLeft: 8 }}>
                  /10 intent
                </span>
              </div>
            )}
            {objection && (
              <div style={{
                fontSize: 22, color: "rgba(240,230,210,0.75)",
                fontStyle: "italic", lineHeight: 1.35,
              }}>
                "{objection}"
              </div>
            )}
          </div>
        </div>
        <div style={{
          fontSize: 16, color: "rgba(240,230,210,0.4)",
          fontFamily: "monospace", letterSpacing: 2, marginTop: 16,
        }}>
          mind.simulatte.io
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
