import { adminFetch } from "@/lib/admin";

interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  personas: number;
  probes: number;
  chats: number;
  last_active: string | null;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 16) + "Z";
}

export default async function AdminUsersPage() {
  const users = (await adminFetch<AdminUser[]>("/admin/users")) ?? [];
  return (
    <div>
      <h1 className="font-condensed font-bold text-parchment text-3xl mb-6">Users ({users.length})</h1>
      <div className="overflow-x-auto border border-parchment/10">
        <table className="w-full text-sm">
          <thead className="bg-parchment/5 text-[10px] font-mono uppercase tracking-widest text-parchment/60">
            <tr>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-right px-4 py-3">Personas</th>
              <th className="text-right px-4 py-3">Probes</th>
              <th className="text-right px-4 py-3">Chats</th>
              <th className="text-left px-4 py-3">Last active</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-parchment/10 hover:bg-parchment/5">
                <td className="px-4 py-3 text-parchment">{u.email}</td>
                <td className="px-4 py-3 text-parchment/70">{u.name ?? "—"}</td>
                <td className="px-4 py-3 text-right font-mono text-parchment">{u.personas}</td>
                <td className="px-4 py-3 text-right font-mono text-parchment">{u.probes}</td>
                <td className="px-4 py-3 text-right font-mono text-parchment">{u.chats}</td>
                <td className="px-4 py-3 text-[11px] font-mono text-parchment/50">{fmt(u.last_active)}</td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-parchment/40 text-sm">No users yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
