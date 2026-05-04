import Link from "next/link";
import { adminFetch } from "@/lib/admin";
import BanControls from "@/components/admin/BanControls";
import ProbeEventActions from "@/components/admin/ProbeEventActions";
import UserChatSessions from "@/components/admin/UserChatSessions";
import UserWeeklyLimitsForm from "@/components/admin/UserWeeklyLimitsForm";

interface UserDetail {
  user: {
    id: string;
    email: string;
    name: string | null;
    banned?: boolean;
    banned_at?: string | null;
    banned_reason?: string | null;
    flagged_count?: number;
    persona_limit_override?: number | null;
    probe_limit_override?: number | null;
    chat_limit_override?: number | null;
    global_limits?: { persona: number; probe: number; chat: number };
  };
  events: Array<{
    id: string;
    type: string;
    ref_id: string | null;
    created_at: string | null;
    persona?: { name: string; age: number; city: string; country: string; portrait_url: string | null };
    probe?: { product_name: string; category: string; purchase_intent: number; top_objection: string; persona_name: string };
    chat?: { persona_name: string; persona_id: string };
  }>;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + "Z";
}

export default async function AdminUserDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await adminFetch<UserDetail>(`/admin/users/${id}`);
  if (!data) return <div className="text-parchment/60">User not found.</div>;
  const { user, events } = data;
  return (
    <div>
      <Link href="/admin/users" className="text-xs font-mono text-parchment/50 hover:text-signal">← Users</Link>
      <h1 className="font-condensed font-bold text-parchment text-3xl mt-4 mb-1">{user.name ?? user.email}</h1>
      <p className="text-parchment/60 text-sm font-mono mb-6">{user.email}</p>

      <BanControls
        userId={user.id}
        banned={!!user.banned}
        bannedReason={user.banned_reason ?? null}
        flaggedCount={user.flagged_count ?? 0}
      />

      {user.global_limits && (
        <div className="mt-4">
          <UserWeeklyLimitsForm
            userId={user.id}
            personaLimitOverride={user.persona_limit_override ?? null}
            probeLimitOverride={user.probe_limit_override ?? null}
            chatLimitOverride={user.chat_limit_override ?? null}
            globalLimits={user.global_limits}
          />
        </div>
      )}

      <UserChatSessions userId={user.id} />

      <h2 className="text-[11px] font-mono uppercase tracking-widest text-parchment/50 mb-4">
        Activity ({events.length})
      </h2>

      <div className="space-y-3">
        {events.map((e) => (
          <div key={e.id} className="border border-parchment/10 p-4">
            <div className="flex items-baseline justify-between gap-4 mb-2">
              <span className="font-mono text-xs text-signal">{e.type}</span>
              <span className="font-mono text-[10px] text-parchment/40">{fmt(e.created_at)}</span>
            </div>
            {e.persona && (
              <div className="flex items-start gap-3">
                {e.persona.portrait_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={e.persona.portrait_url} alt="" className="w-12 h-12 object-cover rounded-sm" />
                )}
                <div className="flex-1">
                  <div className="text-parchment text-sm">
                    {e.persona.name}{e.persona.age ? `, ${e.persona.age}` : ""}
                  </div>
                  <div className="text-parchment/60 text-xs">
                    {[e.persona.city, e.persona.country].filter(Boolean).join(", ")}
                  </div>
                  {e.ref_id && (
                    <Link href={`/persona/${e.ref_id}`} target="_blank" className="text-signal text-xs font-mono hover:underline">
                      open ↗
                    </Link>
                  )}
                </div>
              </div>
            )}
            {e.probe && (
              <div>
                <div className="text-parchment text-sm mb-1">
                  <span className="text-parchment/60">{e.probe.persona_name} on </span>
                  {e.probe.product_name}
                  <span className="ml-3 font-mono text-signal text-xs">intent {e.probe.purchase_intent}/10</span>
                </div>
                <div className="text-parchment/60 text-xs italic">"{e.probe.top_objection}"</div>
                {e.ref_id && (
                  <Link href={`/probe/${e.ref_id}`} target="_blank" className="text-signal text-xs font-mono hover:underline">
                    open ↗
                  </Link>
                )}
                {e.type === "probe_run" && e.ref_id && (
                  <ProbeEventActions probeId={e.ref_id} />
                )}
              </div>
            )}
            {e.chat && (
              <div className="text-parchment/70 text-sm">
                Chat with <span className="text-parchment">{e.chat.persona_name}</span>
              </div>
            )}
            {!e.persona && !e.probe && !e.chat && e.ref_id && (
              <div className="font-mono text-[11px] text-parchment/50">{e.ref_id}</div>
            )}
          </div>
        ))}
        {events.length === 0 && (
          <p className="text-parchment/40 text-sm text-center py-6">No activity yet.</p>
        )}
      </div>
    </div>
  );
}
