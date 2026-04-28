import Link from "next/link";
import { adminFetch } from "@/lib/admin";
import AdminPersonaActions from "@/components/AdminPersonaActions";
import RegenerateAllPortraits from "@/components/RegenerateAllPortraits";

interface AdminPersona {
  persona_id: string;
  name: string;
  age: number | null;
  city: string | null;
  country: string | null;
  creator_email: string;
  creator_name: string | null;
  created_at: string | null;
  portrait_url: string | null;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 16) + "Z";
}

export default async function AdminPersonasPage() {
  const rows = (await adminFetch<AdminPersona[]>("/admin/personas")) ?? [];
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-condensed font-bold text-parchment text-3xl">Personas ({rows.length})</h1>
        <RegenerateAllPortraits />
      </div>
      <div className="overflow-x-auto border border-parchment/10">
        <table className="w-full text-sm">
          <thead className="bg-parchment/5 text-[10px] font-mono uppercase tracking-widest text-parchment/60">
            <tr>
              <th className="text-left px-4 py-3">Persona</th>
              <th className="text-left px-4 py-3">Where</th>
              <th className="text-left px-4 py-3">Creator</th>
              <th className="text-left px-4 py-3">Created</th>
              <th className="text-left px-4 py-3">Link</th>
              <th className="text-left px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.persona_id} className="border-t border-parchment/10 hover:bg-parchment/5">
                <td className="px-4 py-3 text-parchment">
                  {p.name}{p.age ? `, ${p.age}` : ""}
                </td>
                <td className="px-4 py-3 text-parchment/70">
                  {[p.city, p.country].filter(Boolean).join(", ") || "—"}
                </td>
                <td className="px-4 py-3 text-parchment/70">{p.creator_email}</td>
                <td className="px-4 py-3 text-[11px] font-mono text-parchment/50">{fmt(p.created_at)}</td>
                <td className="px-4 py-3">
                  <Link
                    href={`/persona/${p.persona_id}`}
                    className="text-signal hover:underline text-xs font-mono"
                    target="_blank"
                  >
                    open ↗
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <AdminPersonaActions personaId={p.persona_id} />
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-parchment/40 text-sm">No personas yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
