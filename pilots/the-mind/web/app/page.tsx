import Link from "next/link";
import { fetchPersonas, PersonaCard } from "@/lib/api";

const STYLE_LABELS: Record<string, string> = {
  analytical: "Analytical", emotional: "Emotional",
  habitual: "Habitual", social: "Social",
};
const VALUE_LABELS: Record<string, string> = {
  price: "Price-first", quality: "Quality-first",
  brand: "Brand-driven", convenience: "Convenience",
  features: "Feature-focused",
};
const TRUST_LABELS: Record<string, string> = {
  self: "Self-reliant", peer: "Peer-driven",
  authority: "Authority", family: "Family",
};

function Badge({ label }: { label: string }) {
  return (
    <span className="inline-block px-2 py-0.5 text-[11px] font-mono font-medium border border-parchment/10 text-static">
      {label}
    </span>
  );
}

function ConsistencyBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2 mt-3">
      <div className="flex-1 h-px bg-parchment/10">
        <div
          className="h-px bg-signal"
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="font-mono text-[10px] text-static">{score}</span>
    </div>
  );
}

function PersonaCardUI({ p }: { p: PersonaCard }) {
  return (
    <Link href={`/${p.slug}`} className="group block border border-parchment/10 p-6 hover:border-parchment/25 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-1">
            {p.life_stage.replace(/_/g, " ")}
          </p>
          <h2 className="font-condensed font-bold text-2xl text-parchment leading-none">
            {p.name}
          </h2>
          <p className="text-static text-sm mt-1">
            {p.age} · {p.city}, {p.country}
          </p>
        </div>
        <div className="text-right">
          <span className="font-mono text-[10px] text-static block">{p.persona_id}</span>
        </div>
      </div>

      <p className="text-sm text-parchment/75 leading-relaxed mb-4 line-clamp-2">
        {p.description}
      </p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <Badge label={STYLE_LABELS[p.decision_style] ?? p.decision_style} />
        <Badge label={VALUE_LABELS[p.primary_value_orientation] ?? p.primary_value_orientation} />
        <Badge label={TRUST_LABELS[p.trust_anchor] ?? p.trust_anchor} />
      </div>

      <ConsistencyBar score={p.consistency_score} />

      <p className="mt-4 text-[11px] font-semibold tracking-widest uppercase text-static group-hover:text-parchment/50 transition-colors">
        Ask a question →
      </p>
    </Link>
  );
}

export default async function Home() {
  let personas: PersonaCard[] = [];
  let error = "";

  try {
    personas = await fetchPersonas();
  } catch {
    error = "API offline — start the backend with: PYTHONPATH=. uvicorn pilots.the_mind_api:app --port 8001";
  }

  return (
    <main className="min-h-screen px-6 py-12 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-12">
        <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-3">
          Simulatte / The Mind
        </p>
        <h1 className="font-condensed font-bold text-parchment leading-none mb-4" style={{ fontSize: "clamp(40px,6vw,72px)" }}>
          Simulate <span className="text-signal">reality.</span>
        </h1>
        <p className="text-parchment/75 text-lg max-w-xl">
          Five synthetic personas. Each one thinks, decides, and reacts like a real person.
          Ask them anything about a product, price, or purchase.
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div className="border border-parchment/15 p-4 mb-8">
          <p className="font-mono text-sm text-static">{error}</p>
        </div>
      )}

      {/* Persona grid */}
      {personas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-parchment/10">
          {personas.map((p) => (
            <div key={p.slug} className="bg-void">
              <PersonaCardUI p={p} />
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-16 pt-6 border-t border-parchment/10 flex items-center justify-between">
        <span className="font-mono text-[10px] text-static">exemplar_set_v1_2026_04</span>
        <span className="font-mono text-[10px] text-static">mind.simulatte.io</span>
      </div>
    </main>
  );
}
