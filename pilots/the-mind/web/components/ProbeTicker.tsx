"use client";

/**
 * ProbeTicker.tsx — horizontal marquee of recent Litmus probe pulses.
 *
 * Each pulse: persona name + product + intent score (parchment, never red)
 * + top-objection snippet. Curated handpicks, not a live feed (privacy).
 *
 * Pure CSS infinite scroll. Brand-compliant: no red, signal green only on
 * the live-dot indicator (one item per surface).
 */

interface Pulse {
  persona: string;       // "Marcus, 41 · Brooklyn"
  product: string;       // "Whoop 5.0"
  intent: number;        // 0-10
  objection: string;     // short snippet
}

const PULSES: Pulse[] = [
  { persona: "Priya, 32 · Mumbai", product: "Premium yoghurt ₹85", intent: 4, objection: "feels like a tax on caring" },
  { persona: "Marcus, 41 · Brooklyn", product: "Whoop 5.0", intent: 3, objection: "$30/mo to confirm I'm tired" },
  { persona: "Margaret, 67 · Devon", product: "Smart thermostat", intent: 2, objection: "if WiFi dies, house goes cold" },
  { persona: "Ravi, 29 · Bangalore", product: "Meal-kit subscription", intent: 6, objection: "novelty wears off by week 3" },
  { persona: "Anjali, 37 · Delhi", product: "₹40k air purifier", intent: 7, objection: "in-laws will judge it as wasteful" },
  { persona: "James, 54 · Manchester", product: "Electric work van", intent: 2, objection: "twelve calls a day, range scares me" },
  { persona: "Linda, 48 · Toronto", product: "AI tutoring app", intent: 5, objection: "kids will copy-paste their way to a B" },
  { persona: "Daniel, 26 · Berlin", product: "Premium SaaS €240/yr", intent: 3, objection: "Figma's free tier does 80% of it" },
  { persona: "Fatima, 39 · Dubai", product: "Personal CGM patch", intent: 2, objection: "I prescribe these, wouldn't wear one" },
  { persona: "Geoffrey, 61 · Edinburgh", product: "Crypto savings app", intent: 1, objection: "8% explained in TikToks = hard no" },
  { persona: "Sophie, 34 · Paris", product: "Plant-based protein", intent: 4, objection: "packaging speaks, taste does not" },
  { persona: "Rajesh, 52 · Chennai", product: "Cloud accounting", intent: 2, objection: "my CA, 18 years, not migrating" },
  { persona: "Olu, 45 · Lagos", product: "EV pickup truck", intent: 2, objection: "Lagos-to-Ibadan, where do I charge" },
  { persona: "Mei, 31 · Singapore", product: "Sleep-tracking ring", intent: 5, objection: "two weeks, then a drawer. I know myself." },
  { persona: "Tomás, 38 · Madrid", product: "DTC mattress", intent: 4, objection: "returning a king-size is my problem" },
  { persona: "Brendan, 35 · Dublin", product: "AI coding assistant", intent: 7, objection: "boilerplate yes, architecture no" },
];

function intentColor(intent: number): string {
  // Brand rule: never red. Strong = parchment-bright; weak = static grey.
  if (intent >= 7) return "text-parchment";
  if (intent >= 5) return "text-parchment/80";
  if (intent >= 3) return "text-parchment/55";
  return "text-static";
}

function PulseChip({ p }: { p: Pulse }) {
  return (
    <div className="inline-flex items-center gap-3 border border-parchment/10 bg-[#0a0a0a] px-4 py-2.5 mx-1.5 whitespace-nowrap">
      <span className="text-parchment/85 text-xs font-medium">{p.persona}</span>
      <span className="text-static text-[10px] font-mono">→</span>
      <span className="text-parchment/65 text-xs">{p.product}</span>
      <span className={`text-[11px] font-mono ${intentColor(p.intent)}`}>
        intent {p.intent}/10
      </span>
      <span className="text-parchment/40 text-[11px] italic">
        &ldquo;{p.objection}&rdquo;
      </span>
    </div>
  );
}

export default function ProbeTicker() {
  // Duplicate the array for seamless infinite scroll
  const stream = [...PULSES, ...PULSES];

  return (
    <section className="border-y border-parchment/8 bg-[#080808] py-6 overflow-hidden">
      <div className="max-w-screen-xl mx-auto px-6 md:px-14 mb-3 flex items-center gap-3">
        <span className="w-2 h-2 bg-signal rounded-full animate-pulse" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-parchment/55">
          Recent probe pulses
        </span>
        <span className="text-[10px] font-mono text-static">— curated sample, privacy-preserving</span>
      </div>
      <div className="relative overflow-hidden">
        {/* Edge fades */}
        <div className="pointer-events-none absolute inset-y-0 left-0 w-24 z-10 bg-gradient-to-r from-[#080808] to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 w-24 z-10 bg-gradient-to-l from-[#080808] to-transparent" />

        <div
          className="flex w-max"
          style={{ animation: "ticker-scroll 90s linear infinite" }}
        >
          {stream.map((p, i) => (
            <PulseChip key={i} p={p} />
          ))}
        </div>
      </div>

      <style>{`
        @keyframes ticker-scroll {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        @media (prefers-reduced-motion: reduce) {
          [style*="ticker-scroll"] { animation: none !important; }
        }
      `}</style>
    </section>
  );
}
