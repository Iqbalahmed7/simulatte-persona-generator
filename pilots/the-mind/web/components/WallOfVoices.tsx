"use client";

/**
 * WallOfVoices.tsx — three vertical columns of drifting persona-quote cards.
 *
 * Visual signal that the system has populated a real, plural mind.
 * Pure CSS animation (translate-Y on infinite loop), respects
 * prefers-reduced-motion, no images required (uses initials in a square).
 *
 * Quotes are curated handpicks, not a live feed — we never auto-surface
 * private user-generated personas on the public landing page.
 */

interface Voice {
  initials: string;
  name: string;
  meta: string;     // "44, Mumbai · Marketing Manager"
  quote: string;    // 1–2 short sentences in first person
  topic: string;    // "Premium yoghurt"
}

// 21 voices — 7 per column, looped 2× for seamless drift.
const VOICES: Voice[] = [
  { initials: "PS", name: "Priya S.", meta: "32, Mumbai · Marketing Manager", topic: "Premium yoghurt", quote: "₹85 for 100g feels like a tax on caring. I'll buy it twice, then go back to Amul." },
  { initials: "MR", name: "Marcus R.", meta: "41, Brooklyn · Construction Foreman", topic: "Whoop 5.0", quote: "I don't need a $30 monthly subscription telling me I'm tired. My back tells me at 5am for free." },
  { initials: "MD", name: "Margaret D.", meta: "67, rural Devon · Retired", topic: "Smart thermostat", quote: "If it needs an app and the WiFi goes, my house goes cold. The dial worked for forty years." },
  { initials: "RK", name: "Ravi K.", meta: "29, Bangalore · Software Engineer", topic: "Meal-kit subscription", quote: "I'll try it for the novelty. By week three I'm ordering Swiggy and the boxes are stacked unopened." },
  { initials: "AN", name: "Anjali N.", meta: "37, Delhi · Pharma Sales", topic: "₹40k air purifier", quote: "My in-laws will judge it as wasteful. I want one anyway. That's the whole story." },
  { initials: "JT", name: "James T.", meta: "54, Manchester · Plumber", topic: "Electric van", quote: "Fine for the bloke down the road who works from home. I do twelve calls a day. Range terrifies me." },
  { initials: "LC", name: "Linda C.", meta: "48, Toronto · School Principal", topic: "Gen-AI tutoring app", quote: "If it doesn't show its working, my Year-9s will copy-paste their way to a B and learn nothing." },
  { initials: "DK", name: "Daniel K.", meta: "26, Berlin · Junior Designer", topic: "Premium SaaS subscription", quote: "I love the design. I cannot justify €240 a year when Figma's free tier does 80% of it." },
  { initials: "FA", name: "Fatima A.", meta: "39, Dubai · GP Doctor", topic: "Personal CGM patch", quote: "I prescribe these. I would not wear one. Watching my own glucose all day is a path to obsession." },
  { initials: "GH", name: "Geoffrey H.", meta: "61, Edinburgh · Accountant", topic: "Crypto savings app", quote: "Anything that promises 8% and explains itself in TikToks gets a hard no from me." },
  { initials: "SO", name: "Sophie O.", meta: "34, Paris · Brand Manager", topic: "Plant-based protein", quote: "The packaging speaks to me. The taste does not. I've bought it three times for the photo, never finished it." },
  { initials: "RP", name: "Rajesh P.", meta: "52, Chennai · Small-business Owner", topic: "Cloud accounting software", quote: "My CA has been doing my books for 18 years. I'm not migrating to a website to save ₹2,000 a month." },
  { initials: "EN", name: "Emma N.", meta: "23, London · Master's Student", topic: "Period-tracking app", quote: "If they sell my data to insurers, I'd rather use a paper diary. Show me the privacy page first." },
  { initials: "OL", name: "Olu L.", meta: "45, Lagos · Logistics Manager", topic: "EV pickup truck", quote: "Where do I charge it? I drive 600km a week. This is a Lagos-to-Ibadan question, not a brochure question." },
  { initials: "MK", name: "Mei K.", meta: "31, Singapore · Product Manager", topic: "Sleep-tracking ring", quote: "I'd buy it. I'd track for two weeks. I'd put it in a drawer. I know myself." },
  { initials: "TB", name: "Tomás B.", meta: "38, Madrid · Architect", topic: "DTC mattress", quote: "A 100-night trial sounds great until you realise returning a king-size to a warehouse is my problem." },
  { initials: "HW", name: "Helen W.", meta: "58, Wellington · Nurse", topic: "Telehealth subscription", quote: "I've watched the GP shortage from inside the system. ₹/$/£ a month is fine if it actually saves me a 3-week wait." },
  { initials: "AY", name: "Ayşe Y.", meta: "44, Istanbul · Teacher", topic: "Online MBA", quote: "My husband thinks it's vanity. My daughter thinks it's overdue. I think it's a $12,000 mid-life argument." },
  { initials: "BS", name: "Brendan S.", meta: "35, Dublin · Dev-Ops Engineer", topic: "AI coding assistant", quote: "For boilerplate, ten out of ten. For the architecture review, I trust my staff engineer over any model." },
  { initials: "NV", name: "Nadia V.", meta: "42, São Paulo · Lawyer", topic: "Luxury skincare set", quote: "R$1,200 for serum is not vanity, it's a small daily proof that the hours I bill are mine." },
  { initials: "CK", name: "Chen K.", meta: "49, Shanghai · Factory Manager", topic: "Industrial IoT platform", quote: "Show me the production-line ROI in yuan. I have eight competing pilots. Yours is the seventh." },
];

// Split into 3 columns by index modulo. Looped 2× per column for seamless scroll.
function columnVoices(offset: number): Voice[] {
  const c: Voice[] = [];
  for (let i = offset; i < VOICES.length; i += 3) c.push(VOICES[i]);
  return [...c, ...c]; // duplicate for infinite-loop seam
}

function VoiceCard({ v }: { v: Voice }) {
  return (
    <div className="bg-[#0a0a0a] border border-parchment/10 p-4 mb-3">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 bg-parchment/8 border border-parchment/15 flex items-center justify-center text-parchment/80 font-condensed font-bold text-xs tracking-wide">
          {v.initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-parchment text-sm font-medium leading-tight truncate">{v.name}</div>
          <div className="text-parchment/45 text-[10px] font-mono truncate">{v.meta}</div>
        </div>
      </div>
      <div className="text-[10px] font-mono uppercase tracking-widest text-static mb-1.5">
        on {v.topic}
      </div>
      <p className="text-parchment/80 text-[13px] leading-relaxed">
        &ldquo;{v.quote}&rdquo;
      </p>
    </div>
  );
}

export default function WallOfVoices() {
  const cols = [columnVoices(0), columnVoices(1), columnVoices(2)];
  // Different speeds per column — drift at independent rates for parallax
  const durations = ["62s", "78s", "70s"];
  const directions = ["up", "down", "up"]; // alternate so middle column counter-flows

  return (
    <section className="px-6 md:px-14 py-20 max-w-screen-xl mx-auto">
      <div className="mb-10">
        <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-3">
          The wall of voices
        </p>
        <h2 className="font-condensed font-bold text-parchment leading-none mb-4"
            style={{ fontSize: "clamp(32px,4.5vw,52px)" }}>
          Twenty-one minds. <span className="text-signal">One sample.</span>
        </h2>
        <p className="text-parchment/55 text-base max-w-2xl leading-relaxed">
          A handful of the people The Mind has simulated. Each speaks in first person — grounded
          in their city, job, household, and the specific tension they hold around the product they&apos;re seeing.
        </p>
      </div>

      {/* 3-column drifting wall — hidden on mobile (replaced with vertical strip) */}
      <div
        className="hidden md:grid grid-cols-3 gap-4 overflow-hidden relative"
        style={{ height: "640px" }}
      >
        {/* Top + bottom fade overlays */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-24 z-10 bg-gradient-to-b from-void to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 z-10 bg-gradient-to-t from-void to-transparent" />

        {cols.map((col, i) => (
          <div key={i} className="relative">
            <div
              className={`wall-col-${i}`}
              style={{
                animation: `wall-drift-${directions[i]} ${durations[i]} linear infinite`,
              }}
            >
              {col.map((v, j) => (
                <VoiceCard key={`${i}-${j}`} v={v} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Mobile: just show first 6 stacked, no animation */}
      <div className="md:hidden space-y-3">
        {VOICES.slice(0, 6).map((v, i) => (
          <VoiceCard key={i} v={v} />
        ))}
        <p className="text-center text-parchment/40 text-xs font-mono pt-2">
          + 15 more
        </p>
      </div>

      <style>{`
        @keyframes wall-drift-up {
          0%   { transform: translateY(0); }
          100% { transform: translateY(-50%); }
        }
        @keyframes wall-drift-down {
          0%   { transform: translateY(-50%); }
          100% { transform: translateY(0); }
        }
        @media (prefers-reduced-motion: reduce) {
          [class^="wall-col-"] { animation: none !important; }
        }
      `}</style>
    </section>
  );
}
