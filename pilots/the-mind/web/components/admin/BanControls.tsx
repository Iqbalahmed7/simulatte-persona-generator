"use client";

/**
 * BanControls.tsx — admin Ban / Unban button on /admin/users/[id].
 *
 * Calls Next.js proxy routes that mint an HS256 admin token and forward to
 * the FastAPI /admin/users/{id}/ban|unban endpoints.
 */
import { useState } from "react";
import { useRouter } from "next/navigation";

interface Props {
  userId: string;
  banned: boolean;
  bannedReason?: string | null;
  flaggedCount: number;
}

export default function BanControls({ userId, banned, bannedReason, flaggedCount }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ban() {
    const reason = window.prompt(
      "Reason for ban (shown to user when they try to act):",
      "violation of usage policy"
    );
    if (!reason) return;
    if (!window.confirm(`Ban this user?\nReason: ${reason}\n\nThey'll be blocked from generate / probe / chat. Reversible.`)) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/users/${userId}/ban`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`${res.status}: ${txt.slice(0, 200)}`);
      }
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "ban failed");
    } finally {
      setBusy(false);
    }
  }

  async function unban() {
    if (!window.confirm("Lift this ban? Resets flagged_count to 0.")) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/users/${userId}/unban`, { method: "POST" });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`${res.status}: ${txt.slice(0, 200)}`);
      }
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "unban failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border border-parchment/10 p-4 mb-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-widest text-parchment/50 mb-1">
            Moderation
          </div>
          <div className="text-sm text-parchment/80">
            Status:{" "}
            {banned ? (
              <span className="text-amber-400/90 font-medium">BANNED</span>
            ) : (
              <span className="text-parchment/60">active</span>
            )}
            <span className="ml-4 text-parchment/40 font-mono text-xs">
              flagged_count = {flaggedCount}
            </span>
          </div>
          {banned && bannedReason && (
            <div className="text-parchment/50 text-xs mt-1">Reason: {bannedReason}</div>
          )}
        </div>
        <div className="flex gap-2">
          {banned ? (
            <button
              onClick={unban}
              disabled={busy}
              className="bg-signal/20 hover:bg-signal/30 border border-signal/40 text-signal text-xs font-mono px-4 py-2 disabled:opacity-50 transition-colors"
            >
              Unban
            </button>
          ) : (
            <button
              onClick={ban}
              disabled={busy}
              className="bg-parchment/5 hover:bg-amber-400/15 border border-amber-400/30 text-amber-400/90 text-xs font-mono px-4 py-2 disabled:opacity-50 transition-colors"
            >
              Ban user
            </button>
          )}
        </div>
      </div>
      {error && <p className="text-amber-400/80 text-xs font-mono mt-2">{error}</p>}
    </div>
  );
}
