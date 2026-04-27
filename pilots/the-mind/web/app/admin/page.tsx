/**
 * /admin — overview tiles: total users, personas, probes, chats, events.
 */
import { adminFetch } from "@/lib/admin";

interface AdminStats {
  users_total: number;
  events_total: number;
  personas_total: number;
  probes_total: number;
  chats_total: number;
  personas_on_disk: number;
}

export default async function AdminHomePage() {
  const stats = await adminFetch<AdminStats>("/admin/stats");
  const tiles = stats
    ? [
        { label: "Users", value: stats.users_total },
        { label: "Personas", value: stats.personas_total },
        { label: "Probes", value: stats.probes_total },
        { label: "Chats", value: stats.chats_total },
        { label: "Events (all)", value: stats.events_total },
        { label: "Personas on disk", value: stats.personas_on_disk },
      ]
    : [];

  return (
    <div>
      <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-3">
        Simulatte / Mind / Operator
      </p>
      <h1 className="font-condensed font-bold text-parchment mb-8" style={{ fontSize: "clamp(32px,4.5vw,52px)" }}>
        Dashboard
      </h1>

      {!stats && (
        <p className="text-parchment/50 text-sm font-mono">
          Stats unavailable — check that ADMIN_EMAILS includes your email on the API.
        </p>
      )}

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {tiles.map((t) => (
            <div key={t.label} className="border border-parchment/10 p-5">
              <div className="text-[10px] font-mono uppercase tracking-widest text-parchment/50 mb-2">
                {t.label}
              </div>
              <div className="font-condensed font-black text-parchment text-4xl">
                {t.value.toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
