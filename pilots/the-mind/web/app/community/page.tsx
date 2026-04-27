/**
 * /community — Community Wall.
 *
 * Public, anonymized grid of every persona generated through The Mind's
 * free tier. Per ToS, free-tier generations are property of Simulatte
 * and surfaced here without any user attribution. Each card links to
 * the persona detail page for read-only browsing.
 *
 * Server component — fetches once per request from FastAPI's
 * /community/personas endpoint, no auth.
 */
import Link from "next/link";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

interface CommunityPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
  snippet: string;
}

async function fetchCommunity(): Promise<CommunityPersona[]> {
  try {
    const res = await fetch(`${API}/community/personas?limit=120`, {
      // ISR — refresh every 60s, no cookies.
      next: { revalidate: 60 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export const metadata = {
  title: "The Wall · Simulatte",
  description: "Every persona simulated by The Mind. Anonymous. Browse, then build your own.",
  openGraph: {
    title: "The Wall — every mind simulated, in one place",
    description: "Browse 60+ behaviourally-coherent personas. Each one is a full life — opinion, contradiction, and all.",
    images: ["/og-default.png"],
  },
};

export default async function CommunityPage() {
  const personas = await fetchCommunity();

  return (
    <main className="min-h-screen bg-void text-parchment">
      {/* Header */}
      <header className="px-6 md:px-14 py-12 max-w-screen-xl mx-auto">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/60 transition-colors">
          ← The Mind
        </Link>

        <div className="mt-8 mb-2">
          <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal">
            Simulatte / The Wall
          </p>
        </div>

        <h1
          className="font-condensed font-black text-parchment leading-none mb-4"
          style={{ fontSize: "clamp(40px, 6vw, 76px)" }}
        >
          Every mind, <span className="text-signal">in one place.</span>
        </h1>

        <p className="text-parchment/65 text-base md:text-lg max-w-2xl leading-relaxed">
          Every persona simulated through The Mind&apos;s free tier lives here. Anonymous —
          we don&apos;t reveal who built whom. Click any card to read the full life,
          chat with them, or run a Litmus probe.
        </p>

        <p className="text-parchment/35 text-xs font-mono mt-6">
          {personas.length} {personas.length === 1 ? "person" : "people"} on the wall · refreshes every minute
        </p>
      </header>

      {/* Grid */}
      <section className="px-6 md:px-14 pb-24 max-w-screen-xl mx-auto">
        {personas.length === 0 ? (
          <div className="border border-parchment/10 p-12 text-center">
            <p className="text-parchment/55 text-sm">
              The wall is quiet right now. Be the first —{" "}
              <Link href="/generate" className="text-signal hover:text-parchment underline underline-offset-2">
                simulate a person
              </Link>
              .
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {personas.map((p) => (
              <Link
                key={p.persona_id}
                href={`/persona/${p.persona_id}`}
                className="group block bg-[#0a0a0a] border border-parchment/10 hover:border-parchment/30 transition-colors"
              >
                {/* Portrait */}
                <div className="relative aspect-square bg-parchment/5 overflow-hidden">
                  {p.portrait_url ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={p.portrait_url}
                      alt=""
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <span className="font-condensed font-black text-parchment/20 text-5xl">
                        {(p.name || "?").slice(0, 2).toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>

                {/* Caption */}
                <div className="p-3">
                  <div className="text-parchment text-sm font-medium leading-tight truncate">
                    {p.name || "Unnamed"}
                  </div>
                  <div className="text-parchment/45 text-[11px] font-mono mt-0.5 truncate">
                    {[p.age || null, p.city, p.country].filter(Boolean).join(" · ")}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Build-your-own CTA */}
        <div className="mt-16 border-t border-parchment/8 pt-12 text-center">
          <p className="text-parchment/55 text-sm mb-4">
            Want a person who isn&apos;t here yet?
          </p>
          <Link
            href="/generate"
            className="inline-block bg-signal text-void font-condensed font-bold px-8 py-3 text-base tracking-wide hover:bg-parchment transition-colors"
          >
            Simulate a new mind →
          </Link>
        </div>

        {/* ToS line */}
        <p className="text-parchment/30 text-[11px] font-mono text-center mt-12 leading-relaxed max-w-xl mx-auto">
          Free-tier personas are public-domain by default and become part of The Wall.
          When paid plans launch, paid generations stay private to you.
          Questions:{" "}
          <a href="mailto:mind@simulatte.io?subject=Community%20Wall" className="text-parchment/55 hover:text-signal underline underline-offset-2">
            mind@simulatte.io
          </a>
        </p>
      </section>
    </main>
  );
}

