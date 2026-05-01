/**
 * app/admin/twins/page.tsx — cross-user Twin table (server component).
 *
 * Uses adminFetch → GET /operator/admin/twins (max 500 rows, desc created_at).
 * Each row links to the owning user's admin detail page.
 */

import Link from "next/link";
import { adminFetch, getAdminUser } from "@/lib/admin";
import { redirect } from "next/navigation";

interface AdminTwin {
  twin_id:           string;
  full_name:         string;
  title:             string | null;
  company:           string | null;
  confidence:        "high" | "medium" | "low";
  last_refreshed_at: string | null;
  is_stale:          boolean;
  probe_count:       number;
  last_frame_score:  number | null;
  portrait_url:      string | null;
  // admin endpoint also returns user_id
  user_id:           string;
}

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 10);
}

function ConfidenceDot({ tier }: { tier: string }) {
  const cls =
    tier === "high"   ? "bg-signal" :
    tier === "medium" ? "bg-parchment/60" :
                        "bg-static/60";
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${cls} mr-1.5`} />;
}

export default async function AdminTwinsPage() {
  const user = await getAdminUser();
  if (!user) redirect("/");

  const twins = await adminFetch<AdminTwin[]>("/operator/admin/twins?limit=500") ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-static text-[10px] font-mono uppercase tracking-wider">Operator</p>
          <h1 className="text-parchment text-lg font-semibold">All Twins</h1>
        </div>
        <span className="text-static text-xs font-mono">{twins.length} total</span>
      </div>

      {twins.length === 0 ? (
        <p className="text-static text-sm py-8 text-center">No Twins built yet.</p>
      ) : (
        <div className="border border-white/8 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/8 bg-white/2">
                {["Subject", "Title / Company", "User", "Confidence", "Probes", "Frame", "Built", ""].map((h) => (
                  <th key={h} className="text-left px-3 py-2 text-static text-[10px] font-mono uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {twins.map((t) => (
                <tr key={t.twin_id} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                  <td className="px-3 py-2">
                    <span className="text-parchment font-medium">{t.full_name}</span>
                    {t.is_stale && (
                      <span className="ml-2 text-[9px] font-mono text-red-400/70 border border-red-500/20 px-1 py-0.5">
                        STALE
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-static text-xs max-w-[180px] truncate">
                    {[t.title, t.company].filter(Boolean).join(" · ") || "—"}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/admin/users/${t.user_id}`}
                      className="text-parchment/70 text-xs font-mono hover:text-signal transition-colors"
                    >
                      {t.user_id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <ConfidenceDot tier={t.confidence} />
                    <span className="text-static text-xs">{t.confidence}</span>
                  </td>
                  <td className="px-3 py-2 text-static text-xs font-mono">{t.probe_count}</td>
                  <td className="px-3 py-2 text-xs font-mono">
                    {t.last_frame_score !== null ? (
                      <span className={t.last_frame_score >= 70 ? "text-signal" : "text-static"}>
                        {t.last_frame_score}
                      </span>
                    ) : (
                      <span className="text-static">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-static text-xs font-mono whitespace-nowrap">
                    {fmt(t.last_refreshed_at)}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/admin/users/${t.user_id}/limits`}
                      className="text-static text-[10px] font-mono hover:text-parchment transition-colors"
                    >
                      limits →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
