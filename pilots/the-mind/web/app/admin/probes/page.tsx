import Link from "next/link";
import { adminFetch } from "@/lib/admin";

interface AdminProbe {
  probe_id: string;
  product_name: string;
  category: string;
  purchase_intent: number | null;
  top_objection: string;
  persona_name: string;
  creator_email: string;
  created_at: string | null;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 16) + "Z";
}

export default async function AdminProbesPage() {
  const rows = (await adminFetch<AdminProbe[]>("/admin/probes")) ?? [];
  return (
    <div>
      <h1 className="font-condensed font-bold text-parchment text-3xl mb-6">Probes ({rows.length})</h1>
      <p className="text-parchment/50 text-sm mb-6">
        Top objection is the most useful field — tells you what users are really testing for.
      </p>
      <div className="overflow-x-auto border border-parchment/10">
        <table className="w-full text-sm">
          <thead className="bg-parchment/5 text-[10px] font-mono uppercase tracking-widest text-parchment/60">
            <tr>
              <th className="text-left px-4 py-3">Product</th>
              <th className="text-left px-4 py-3">Persona</th>
              <th className="text-right px-4 py-3">Intent</th>
              <th className="text-left px-4 py-3 max-w-md">Top objection</th>
              <th className="text-left px-4 py-3">Creator</th>
              <th className="text-left px-4 py-3">Created</th>
              <th className="text-left px-4 py-3">Link</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.probe_id} className="border-t border-parchment/10 hover:bg-parchment/5 align-top">
                <td className="px-4 py-3 text-parchment">{p.product_name}</td>
                <td className="px-4 py-3 text-parchment/70">{p.persona_name}</td>
                <td className="px-4 py-3 text-right font-mono text-signal">
                  {p.purchase_intent ?? "—"}
                </td>
                <td className="px-4 py-3 text-parchment/70 text-xs max-w-md">
                  {p.top_objection || "—"}
                </td>
                <td className="px-4 py-3 text-parchment/70 text-xs">{p.creator_email}</td>
                <td className="px-4 py-3 text-[11px] font-mono text-parchment/50">{fmt(p.created_at)}</td>
                <td className="px-4 py-3">
                  <Link
                    href={`/probe/${p.probe_id}`}
                    className="text-signal hover:underline text-xs font-mono"
                    target="_blank"
                  >
                    open ↗
                  </Link>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-parchment/40 text-sm">No probes yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
