/**
 * /admin/flagged — list of moderation_blocked events.
 *
 * Each row links to the offending user's detail page where the admin
 * can ban / unban from the BanControls component.
 */
import Link from "next/link";
import { adminFetch } from "@/lib/admin";

interface FlaggedItem {
  id: string;
  user_id: string;
  user_email: string;
  user_banned: boolean;
  user_flagged_count: number;
  ref_id: string | null;
  created_at: string | null;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + "Z";
}

function parseRef(ref: string | null): { reason: string; surface: string; terms: string } {
  if (!ref) return { reason: "?", surface: "?", terms: "" };
  const [reason, surface, ...rest] = ref.split(":");
  return { reason: reason ?? "?", surface: surface ?? "?", terms: rest.join(":") };
}

export default async function FlaggedPage() {
  const items = await adminFetch<FlaggedItem[]>("/admin/flagged");
  if (!items) return <div className="text-parchment/60">Failed to load flagged events.</div>;
  return (
    <div>
      <h1 className="font-condensed font-bold text-parchment text-3xl mb-1">Flagged</h1>
      <p className="text-parchment/50 text-sm mb-8">
        Inputs blocked by content moderation. 3+ flags = automatic ban.
      </p>
      <div className="border border-parchment/10">
        <div className="grid grid-cols-[1fr_120px_120px_140px_180px] gap-4 px-4 py-3 border-b border-parchment/10 text-[10px] font-mono uppercase tracking-widest text-parchment/40">
          <div>User</div>
          <div>Surface</div>
          <div>Reason</div>
          <div>Status</div>
          <div>When</div>
        </div>
        {items.length === 0 && (
          <p className="text-parchment/40 text-sm text-center py-8">No flagged events yet — good sign.</p>
        )}
        {items.map((it) => {
          const p = parseRef(it.ref_id);
          return (
            <Link
              key={it.id}
              href={`/admin/users/${it.user_id}`}
              className="grid grid-cols-[1fr_120px_120px_140px_180px] gap-4 px-4 py-3 border-b border-parchment/5 hover:bg-parchment/5 transition-colors text-sm"
            >
              <div className="text-parchment truncate">{it.user_email}</div>
              <div className="text-parchment/60 font-mono text-xs">{p.surface}</div>
              <div className="text-amber-400/80 font-mono text-xs">{p.reason}</div>
              <div className="text-xs font-mono">
                {it.user_banned ? (
                  <span className="text-amber-400/90">banned</span>
                ) : (
                  <span className="text-parchment/50">{it.user_flagged_count}/3 flags</span>
                )}
              </div>
              <div className="text-parchment/40 font-mono text-[11px]">{fmt(it.created_at)}</div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
