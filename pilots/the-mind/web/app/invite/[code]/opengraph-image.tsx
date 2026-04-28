/**
 * OG card for /invite/[code] — what WhatsApp / LinkedIn / iMessage show
 * when someone shares a Mind invite link.
 *
 * Two-column layout:
 *   Left  — brand pitch: Engine mark, "you're invited" eyebrow,
 *           "Talk to a person who doesn't exist." hero, sub-line.
 *   Right — a random community persona: portrait, name + age, city,
 *           one-line snippet. Adds intrigue: the recipient sees an
 *           actual fake person staring back at them.
 *
 * Brand-locked: void background, parchment text, single signal-green
 * accent on the Engine mark dot. No gradients, no rounded corners.
 *
 * Fallback: if the community endpoint is slow or empty, we render a
 * pitch-only card so the share still looks good.
 */
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "You've been invited to The Mind";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

type CommunityPersona = {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
  snippet: string;
};

async function pickPersona(): Promise<CommunityPersona | null> {
  try {
    const res = await fetch(`${API}/community/personas?limit=30`, {
      // 5-minute edge cache — crawlers hit this URL repeatedly when
      // unfurling, no need to thrash the API.
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const list = (await res.json()) as CommunityPersona[];
    const withPortraits = list.filter((p) => p.portrait_url && p.name);
    if (withPortraits.length === 0) return null;
    return withPortraits[Math.floor(Math.random() * withPortraits.length)];
  } catch {
    return null;
  }
}

function EngineMark({ size: s = 36 }: { size?: number }) {
  return (
    <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
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
  );
}

export default async function Image() {
  const persona = await pickPersona();

  // Left column — pitch
  const Left = (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        paddingRight: 56,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <EngineMark size={36} />
        <span
          style={{
            color: "#E9E6DF",
            fontSize: 20,
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
            fontSize: 12,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            marginLeft: 4,
          }}
        >
          by Simulatte
        </span>
      </div>

      <div style={{ flex: 1 }} />

      <div
        style={{
          color: "#A8FF3E",
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: "0.20em",
          textTransform: "uppercase",
          marginBottom: 16,
        }}
      >
        You're invited
      </div>

      <div
        style={{
          color: "#E9E6DF",
          fontSize: 64,
          fontWeight: 800,
          lineHeight: 0.98,
          letterSpacing: "-0.01em",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <span>Talk to a person</span>
        <span>who doesn't exist.</span>
      </div>

      <div
        style={{
          color: "rgba(233,230,223,0.72)",
          fontSize: 20,
          lineHeight: 1.4,
          marginTop: 24,
          maxWidth: 540,
        }}
      >
        The Mind builds a behaviourally coherent synthetic person from a
        paragraph — then lets you simulate any decision they'd make.
      </div>

      <div
        style={{
          color: "#9A9997",
          fontSize: 12,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          marginTop: 28,
        }}
      >
        mind.simulatte.io
      </div>
    </div>
  );

  // Right column — persona card (only when we have one)
  const Right = persona ? (
    <div
      style={{
        width: 360,
        display: "flex",
        flexDirection: "column",
        border: "1px solid rgba(233,230,223,0.12)",
        background: "rgba(233,230,223,0.02)",
      }}
    >
      {persona.portrait_url ? (
        <img
          src={persona.portrait_url}
          width={360}
          height={360}
          style={{ width: 360, height: 360, objectFit: "cover" }}
        />
      ) : (
        <div style={{ width: 360, height: 360, background: "#0c0c0c", display: "flex" }} />
      )}
      <div
        style={{
          padding: "20px 22px 22px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            color: "#9A9997",
            fontSize: 11,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            marginBottom: 8,
          }}
        >
          Generated · ID {persona.persona_id.slice(0, 8)}
        </div>
        <div
          style={{
            color: "#E9E6DF",
            fontSize: 22,
            fontWeight: 700,
            lineHeight: 1.1,
            marginBottom: 4,
          }}
        >
          {persona.name}
          {persona.age ? `, ${persona.age}` : ""}
        </div>
        {(persona.city || persona.country) && (
          <div
            style={{
              color: "rgba(233,230,223,0.72)",
              fontSize: 14,
              marginBottom: 12,
            }}
          >
            {[persona.city, persona.country].filter(Boolean).join(" · ")}
          </div>
        )}
        {persona.snippet && (
          <div
            style={{
              color: "rgba(233,230,223,0.68)",
              fontSize: 13,
              lineHeight: 1.5,
              display: "-webkit-box",
              // @ts-expect-error — satori supports this
              WebkitLineClamp: 3,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {persona.snippet}
          </div>
        )}
      </div>
    </div>
  ) : null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#050505",
          display: "flex",
          padding: "56px 64px",
          fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
        }}
      >
        {Left}
        {Right}
      </div>
    ),
    { ...size }
  );
}
