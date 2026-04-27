/**
 * /admin/referrals — referral tree.
 *
 * Each row is an inviter; expanding shows everyone they brought in.
 * The leaderboard sort surfaces top spreaders first — your viral
 * growth signal in private launch.
 */
import { adminFetch } from "@/lib/admin";

export const dynamic = "force-dynamic";

interface Downstream {
  id: string;
  email: string;
  name: string | null;
  access_status: string;
}

interface InviterRow {
  inviter_id: string;
  inviter_email: string;
  inviter_name: string | null;
  personal_invite_code: string | null;
  downstream_count: number;
  downstream: Downstream[];
}

export default async function AdminReferralsPage() {
  const rows = (await adminFetch<InviterRow[]>("/admin/referrals")) ?? [];
  const total = rows.reduce((s, r) => s + r.downstream_count, 0);
  return (
    <div>
      <h1 className="font-condensed font-black text-3xl uppercase tracking-wider mb-2">
        Referral Tree
      </h1>
      <p className="text-parchment/72 mb-2 max-w-2xl">
        Who brought whom. {rows.length} inviter{rows.length === 1 ? "" : "s"}{" "}
        have collectively brought {total} downstream user{total === 1 ? "" : "s"}.
      </p>
      <p className="text-parchment/40 text-sm mb-8 max-w-2xl">
        Admin-issued codes don&#x2019;t appear here — only redemptions of a
        user&#x2019;s personal reshare code count toward the tree.
      </p>

      {rows.length === 0 && (
        <p className="text-parchment/40 py-8 text-center">
          No referral redemptions yet.
        </p>
      )}

      <div className="space-y-4">
        {rows.map((r) => (
          <details key={r.inviter_id} className="border border-parchment/10 p-5 group">
            <summary className="flex items-center justify-between cursor-pointer list-none">
              <div className="flex items-baseline gap-3">
                <span className="font-condensed font-bold text-parchment text-lg">
                  {r.inviter_name ?? "(no name)"}
                </span>
                <span className="font-mono text-xs text-parchment/60">
                  {r.inviter_email}
                </span>
              </div>
              <div className="flex items-center gap-4">
                {r.personal_invite_code && (
                  <span className="font-mono text-[10px] text-static tracking-widest uppercase">
                    code: <span className="text-parchment/80">{r.personal_invite_code}</span>
                  </span>
                )}
                <span className="font-condensed font-black text-signal text-xl">
                  {r.downstream_count}
                </span>
              </div>
            </summary>
            <ul className="mt-4 space-y-2 pl-4 border-l border-parchment/10">
              {r.downstream.map((d) => (
                <li key={d.id} className="flex items-center justify-between">
                  <div>
                    <span className="font-condensed font-bold text-parchment">
                      {d.name ?? "(no name)"}
                    </span>{" "}
                    <a href={`mailto:${d.email}`} className="font-mono text-xs text-parchment/60">
                      {d.email}
                    </a>
                  </div>
                  <span
                    className={
                      "font-mono text-[10px] tracking-widest uppercase " +
                      (d.access_status === "active" ? "text-signal" : "text-parchment/40")
                    }
                  >
                    {d.access_status}
                  </span>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
    </div>
  );
}
