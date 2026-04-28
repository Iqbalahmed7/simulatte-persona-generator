/**
 * ReferralCard — prominent "invite a friend" surface on the dashboard.
 *
 * Surfaces the user's personal_invite_code (auto-minted at redeem /
 * approval time, returned by /me) as a shareable URL. Uses the Web
 * Share API on mobile so the user can fire off the link via WhatsApp /
 * Messages / Mail in two taps; falls back to copy-to-clipboard
 * everywhere else.
 *
 * The shared URL is /invite/[code], which already has a branded OG
 * card (opengraph-image.tsx in that segment) so previews look
 * intentional in WhatsApp / iMessage / LinkedIn.
 */
"use client";

import { useEffect, useState } from "react";

export default function ReferralCard({
  code,
  variant = "default",
}: {
  code: string | null;
  variant?: "default" | "compact";
}) {
  const [origin, setOrigin] = useState("");
  const [copied, setCopied] = useState(false);
  const [canShare, setCanShare] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setOrigin(window.location.origin);
    setCanShare(typeof navigator !== "undefined" && !!navigator.share);
  }, []);

  if (!code) return null;

  const url = `${origin}/invite/${encodeURIComponent(code)}`;
  const shareText =
    "I'm using The Mind — you can talk to a synthetic person built from a paragraph. Worth a look:";

  async function handleShare() {
    if (canShare) {
      try {
        await navigator.share({
          title: "The Mind — invite",
          text: shareText,
          url,
        });
        return;
      } catch {
        // user dismissed share sheet — fall through to copy
      }
    }
    await copy();
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // older browsers — no-op; user can long-press to copy
    }
  }

  if (variant === "compact") {
    return (
      <button
        type="button"
        onClick={handleShare}
        className="w-full text-left border border-parchment/15 hover:border-signal/50 transition-colors p-3"
      >
        <p className="text-[10px] font-mono text-signal tracking-widest uppercase mb-1">
          Invite a friend
        </p>
        <p className="text-parchment text-sm font-condensed font-bold leading-tight">
          {canShare ? "Share your link →" : copied ? "Copied!" : "Copy your link"}
        </p>
      </button>
    );
  }

  return (
    <div className="border border-signal/40 bg-signal/[0.04] p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <p className="text-[10px] font-mono text-signal tracking-widest uppercase mb-2">
            Invite a friend
          </p>
          <h3 className="font-condensed font-bold text-parchment text-xl sm:text-2xl leading-tight">
            Bring someone into The Mind.
          </h3>
        </div>
      </div>
      <p className="text-parchment/72 text-sm leading-relaxed mb-4 max-w-md">
        Your personal invite link. Whoever joins through it shows up on your
        referral tree.
      </p>

      {/* URL preview */}
      <div className="bg-void border border-parchment/10 px-3 py-2.5 mb-4 overflow-hidden">
        <p
          className="font-mono text-[11px] sm:text-xs text-parchment/85 truncate"
          title={url}
        >
          {url || `…/invite/${code}`}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleShare}
          className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-5 py-2.5 text-sm hover:opacity-90 transition-opacity"
        >
          {canShare ? "Share link →" : copied ? "Copied!" : "Copy link"}
        </button>
        {canShare && (
          <button
            type="button"
            onClick={copy}
            className="border border-parchment/20 text-parchment font-condensed font-bold uppercase tracking-wider px-5 py-2.5 text-sm hover:border-parchment/40 transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        )}
      </div>
    </div>
  );
}
