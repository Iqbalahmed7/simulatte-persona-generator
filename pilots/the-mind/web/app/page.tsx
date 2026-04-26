import { fetchPersonas, PersonaCard } from "@/lib/api";
import PersonaGrid from "@/components/PersonaGrid";
import Link from "next/link";

export default async function Home() {
  let personas: PersonaCard[] = [];
  let error = "";

  try {
    personas = await fetchPersonas();
  } catch {
    error = "API offline — start the backend with: PYTHONPATH=. uvicorn pilots.the_mind_api:app --port 8001";
  }

  return (
    <main className="min-h-screen px-4 py-8 md:px-6 md:py-12 max-w-6xl mx-auto">
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
          200+ attributes. Full decision psychology. Ask them anything.
        </p>
        <div className="mt-6">
          <Link
            href="/generate"
            className="inline-block px-6 py-3 bg-signal text-void font-condensed font-bold text-base
                       tracking-wide hover:bg-parchment transition-colors"
          >
            Generate a new persona →
          </Link>
        </div>
      </div>

      {error && (
        <div className="border border-parchment/15 p-4 mb-8">
          <p className="font-mono text-sm text-static">{error}</p>
        </div>
      )}

      {personas.length > 0 && <PersonaGrid personas={personas} />}

      {/* Footer */}
      <div className="mt-16 pt-6 border-t border-parchment/10 flex items-center justify-between">
        <span className="font-mono text-[10px] text-static">exemplar_set_v1_2026_04</span>
        <span className="font-mono text-[10px] text-static">mind.simulatte.io</span>
      </div>
    </main>
  );
}
