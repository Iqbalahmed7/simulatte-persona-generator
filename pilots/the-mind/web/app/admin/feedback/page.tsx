/**
 * /admin/feedback — NPS + qualitative feedback log.
 *
 * Pulls every user feedback entry, surfaces the rolling NPS score and
 * average so the operator can see sentiment at a glance.
 */
import { adminFetch } from "@/lib/admin";

interface FeedbackEntry {
  created_at: string | null;
  email: string;
  name: string | null;
  score: number | null;
  comment: string | null;
  surface: string | null;
}

interface FeedbackResponse {
  count: number;
  nps: number;
  avg: number;
  entries: FeedbackEntry[];
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 16) + "Z";
}

function tone(score: number | null): string {
  if (score == null) return "text-parchment/50";
  if (score >= 9) return "text-signal";
  if (score >= 7) return "text-parchment";
  return "text-static";
}

export default async function AdminFeedbackPage() {
  const data =
    (await adminFetch<FeedbackResponse>("/admin/feedback")) ??
    { count: 0, nps: 0, avg: 0, entries: [] as FeedbackEntry[] };

  return (
    <div>
      <h1 className="font-condensed font-bold text-parchment text-3xl mb-6">
        Feedback ({data.count})
      </h1>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
        <Stat label="NPS" value={String(data.nps)} accent={data.nps >= 0 ? "signal" : "static"} />
        <Stat label="Avg score" value={data.avg.toFixed(1)} />
        <Stat label="Responses" value={String(data.count)} />
      </div>

      <div className="overflow-x-auto border border-parchment/10">
        <table className="w-full text-sm">
          <thead className="bg-parchment/5 text-[10px] font-mono uppercase tracking-widest text-parchment/60">
            <tr>
              <th className="text-left px-4 py-3">When</th>
              <th className="text-left px-4 py-3">User</th>
              <th className="text-left px-4 py-3">Score</th>
              <th className="text-left px-4 py-3">Surface</th>
              <th className="text-left px-4 py-3">Comment</th>
            </tr>
          </thead>
          <tbody>
            {data.entries.map((e, i) => (
              <tr key={i} className="border-t border-parchment/10 hover:bg-parchment/5">
                <td className="px-4 py-3 text-[11px] font-mono text-parchment/50">{fmt(e.created_at)}</td>
                <td className="px-4 py-3 text-parchment">
                  {e.name || e.email}
                  {e.name && <span className="text-parchment/40 ml-2 text-xs">{e.email}</span>}
                </td>
                <td className={"px-4 py-3 font-mono " + tone(e.score)}>{e.score ?? "—"}</td>
                <td className="px-4 py-3 text-parchment/60 text-xs font-mono">{e.surface || "—"}</td>
                <td className="px-4 py-3 text-parchment/80">{e.comment || <span className="text-parchment/30">—</span>}</td>
              </tr>
            ))}
            {data.entries.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-parchment/40 text-sm">No feedback yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: "signal" | "static" }) {
  const color = accent === "signal" ? "text-signal" : accent === "static" ? "text-static" : "text-parchment";
  return (
    <div className="border border-parchment/10 p-4">
      <p className="text-[10px] font-mono text-parchment/50 uppercase tracking-[0.18em] mb-2">{label}</p>
      <p className={"font-condensed font-bold text-3xl " + color}>{value}</p>
    </div>
  );
}
