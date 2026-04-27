import { adminFetch } from "@/lib/admin";

interface AdminEvent {
  id: string;
  type: string;
  user_email: string;
  ref_id: string | null;
  created_at: string | null;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + "Z";
}

export default async function AdminEventsPage() {
  const rows = (await adminFetch<AdminEvent[]>("/admin/events")) ?? [];
  return (
    <div>
      <h1 className="font-condensed font-bold text-parchment text-3xl mb-6">Event firehose ({rows.length})</h1>
      <p className="text-parchment/50 text-sm mb-6">
        Most recent first. Last 200 events.
      </p>
      <div className="overflow-x-auto border border-parchment/10">
        <table className="w-full text-sm">
          <thead className="bg-parchment/5 text-[10px] font-mono uppercase tracking-widest text-parchment/60">
            <tr>
              <th className="text-left px-4 py-3">When</th>
              <th className="text-left px-4 py-3">Type</th>
              <th className="text-left px-4 py-3">User</th>
              <th className="text-left px-4 py-3">Ref ID</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.id} className="border-t border-parchment/10 hover:bg-parchment/5">
                <td className="px-4 py-3 text-[11px] font-mono text-parchment/60">{fmt(e.created_at)}</td>
                <td className="px-4 py-3 font-mono text-xs text-signal">{e.type}</td>
                <td className="px-4 py-3 text-parchment/70 text-xs">{e.user_email}</td>
                <td className="px-4 py-3 font-mono text-[11px] text-parchment/50">{e.ref_id ?? "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-parchment/40 text-sm">No events yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
