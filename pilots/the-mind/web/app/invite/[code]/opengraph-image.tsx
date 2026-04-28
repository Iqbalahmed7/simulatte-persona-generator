/**
 * OG card for /invite/[code] — what WhatsApp / LinkedIn / iMessage show
 * when someone shares a Mind invite link.
 *
 * Brand-locked palette only: void background, parchment text, single
 * signal-green accent on the Engine mark dot. No gradients, no rounded
 * corners, no third font.
 */
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "You've been invited to The Mind";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#050505",
          display: "flex",
          flexDirection: "column",
          padding: "72px 88px",
          fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
        }}
      >
        {/* Top row: Engine mark + wordmark */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
            <path
              d="M 10,26.392 A 12,12 0 1 0 10,5.608"
              stroke="#E9E6DF"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
            <path
              d="M 12.5,22.062 A 7,7 0 1 0 12.5,9.938"
              stroke="#E9E6DF"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
            <circle cx="16" cy="16" r="3.2" fill="#A8FF3E" />
          </svg>
          <span
            style={{
              color: "#E9E6DF",
              fontSize: 22,
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            The Mind
          </span>
          <span
            style={{
              color: "#9A9997",
              fontSize: 14,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              marginLeft: 6,
            }}
          >
            by Simulatte
          </span>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Eyebrow */}
        <div
          style={{
            color: "#A8FF3E",
            fontSize: 16,
            fontWeight: 600,
            letterSpacing: "0.20em",
            textTransform: "uppercase",
            marginBottom: 18,
          }}
        >
          You're invited
        </div>

        {/* Hero — split lettering: parchment + parchment, no green word
            here so we don't burn the green budget twice on one card */}
        <div
          style={{
            color: "#E9E6DF",
            fontSize: 92,
            fontWeight: 800,
            lineHeight: 0.96,
            letterSpacing: "-0.01em",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <span>Talk to a person</span>
          <span>who doesn't exist.</span>
        </div>

        {/* Subline */}
        <div
          style={{
            color: "rgba(233,230,223,0.72)",
            fontSize: 26,
            lineHeight: 1.4,
            marginTop: 28,
            maxWidth: 880,
          }}
        >
          The Mind generates a behaviourally coherent synthetic person from a
          paragraph — then lets you simulate any decision they'd make.
        </div>

        {/* Footer URL */}
        <div
          style={{
            color: "#9A9997",
            fontSize: 14,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            marginTop: 36,
          }}
        >
          mind.simulatte.io
        </div>
      </div>
    ),
    { ...size }
  );
}
