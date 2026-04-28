/**
 * ReferralCard — prominent "invite a friend" surface on the dashboard.
 *
 * Surfaces the user's personal_invite_code (auto-minted at redeem /
 * approval time, returned by /me) as a shareable URL.
 *
 * On mobile, the previous version called navigator.share() which on
 * iOS Safari + Brave falls through to web URLs — WhatsApp opened the
 * App Store, LinkedIn dumped users on its sign-in page. Now we use
 * explicit per-app deeplinks so the native app opens directly:
 *
 *   WhatsApp →  whatsapp://send?text=…           opens the app, ready to pick contact
 *   Telegram →  https://t.me/share/url?url=…     opens Telegram app, pre-filled
 *   iMessage →  sms:&body=…                       opens Messages app
 *   Email    →  mailto:?subject=&body=            opens Mail app
 *   X        →  https://twitter.com/intent/tweet  opens X app on iOS/Android
 *   LinkedIn →  copy + nudge (no reliable mobile  deeplink — LI killed it)
 *   Copy     →  clipboard
 *
 * The shared URL is /invite/[code], which already has a branded OG
 * card so previews look intentional in WhatsApp / iMessage / Telegram.
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

  useEffect(() => {
    if (typeof window === "undefined") return;
    setOrigin(window.location.origin);
  }, []);

  if (!code) return null;

  const url = origin ? `${origin}/invite/${encodeURIComponent(code)}` : "";
  const message = `I'm using The Mind — you can talk to a synthetic person built from a paragraph. Worth a look: ${url}`;

  // Encoded variants used by the deeplinks below.
  const eMsg = encodeURIComponent(message);
  const eUrl = encodeURIComponent(url);
  const eText = encodeURIComponent("Talk to a person who doesn't exist — The Mind by Simulatte");

  // Per-app deeplinks. The whatsapp:// scheme opens the installed app
  // directly on iOS/Android; the wa.me fallback only fires if the user
  // long-presses or the scheme is blocked.
  const links = {
    whatsapp: `whatsapp://send?text=${eMsg}`,
    telegram: `https://t.me/share/url?url=${eUrl}&text=${eText}`,
    sms: `sms:&body=${eMsg}`,
    email: `mailto:?subject=${encodeURIComponent("You're invited to The Mind")}&body=${eMsg}`,
    x: `https://twitter.com/intent/tweet?url=${eUrl}&text=${eText}`,
  };

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // older browsers — long-press to copy
    }
  }

  if (variant === "compact") {
    return (
      <button
        type="button"
        onClick={copy}
        className="w-full text-left border border-parchment/15 hover:border-signal/50 transition-colors p-3"
      >
        <p className="text-[10px] font-mono text-signal tracking-widest uppercase mb-1">
          Invite a friend
        </p>
        <p className="text-parchment text-sm font-condensed font-bold leading-tight">
          {copied ? "Link copied" : "Copy your invite link"}
        </p>
      </button>
    );
  }

  return (
    <div className="border border-signal/40 bg-signal/[0.04] p-5 sm:p-6">
      <p className="text-[10px] font-mono text-signal tracking-widest uppercase mb-2">
        Invite a friend
      </p>
      <h3 className="font-condensed font-bold text-parchment text-xl sm:text-2xl leading-tight mb-2">
        Bring someone into The Mind.
      </h3>
      <p className="text-parchment/72 text-sm leading-relaxed mb-4 max-w-md">
        Whoever joins through your link shows up on your referral tree.
      </p>

      {/* URL preview + copy */}
      <div className="flex gap-2 mb-4">
        <div className="flex-1 min-w-0 bg-void border border-parchment/10 px-3 py-3 overflow-hidden">
          <p
            className="font-mono text-[12px] sm:text-xs text-parchment/85 truncate"
            title={url}
          >
            {url || `…/invite/${code}`}
          </p>
        </div>
        <button
          type="button"
          onClick={copy}
          aria-label="Copy invite link"
          className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-4 text-sm hover:opacity-90 transition-opacity"
          style={{ minHeight: 48 }}
        >
          {copied ? "✓" : "Copy"}
        </button>
      </div>

      {/* App-specific share row — these deeplinks open the native app
          directly on mobile. Desktop falls through to web versions. */}
      <p className="text-[10px] font-mono text-static tracking-widest uppercase mb-2.5">
        Share via
      </p>
      <div className="grid grid-cols-5 gap-2">
        <ShareButton href={links.whatsapp} label="WhatsApp" icon={<IconWhatsApp />} />
        <ShareButton href={links.telegram} label="Telegram" icon={<IconTelegram />} external />
        <ShareButton href={links.sms} label="iMessage" icon={<IconSMS />} />
        <ShareButton href={links.email} label="Email" icon={<IconEmail />} />
        <ShareButton href={links.x} label="X" icon={<IconX />} external />
      </div>

      <p className="text-parchment/50 text-[11px] mt-4 leading-relaxed">
        For LinkedIn, copy the link above and paste it into your post — LinkedIn&#x2019;s
        share sheet doesn&#x2019;t reliably open the mobile app.
      </p>
    </div>
  );
}

function ShareButton({
  href,
  label,
  icon,
  external = false,
}: {
  href: string;
  label: string;
  icon: React.ReactNode;
  external?: boolean;
}) {
  return (
    <a
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      aria-label={`Share via ${label}`}
      className="flex flex-col items-center justify-center gap-1.5 border border-parchment/15 hover:border-signal/50 active:bg-parchment/5 transition-colors py-3"
      style={{ minHeight: 64 }}
    >
      <span className="text-parchment/85">{icon}</span>
      <span className="font-mono text-[9px] text-parchment/70 tracking-widest uppercase">
        {label}
      </span>
    </a>
  );
}

/* ────────────────────────── icons ────────────────────────── */

function IconWhatsApp() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.5 14.4c-.3-.1-1.7-.8-2-.9s-.5-.1-.6.1-.7.9-.9 1.1-.3.2-.6.1c-.3-.1-1.2-.4-2.4-1.4-.9-.8-1.5-1.8-1.6-2.1s0-.4.1-.5l.4-.4c.1-.1.2-.3.3-.4.1-.2.1-.3 0-.5s-.6-1.4-.8-1.9c-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.4.1-.6.3-.2.2-.8.8-.8 2s.8 2.3 1 2.5 1.7 2.6 4.1 3.6c.6.2 1 .4 1.4.5.6.2 1.1.2 1.6.1.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.6-.3zM12 2A10 10 0 0 0 2 12c0 1.8.5 3.5 1.3 5L2 22l5.2-1.4A10 10 0 0 0 22 12c0-2.7-1-5.2-2.9-7.1A10 10 0 0 0 12 2zm0 18.3c-1.6 0-3.2-.4-4.5-1.2l-.3-.2-3 .8.8-2.9-.2-.3a8.3 8.3 0 1 1 7.2 3.8z" />
    </svg>
  );
}

function IconTelegram() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
    </svg>
  );
}

function IconSMS() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function IconEmail() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  );
}

function IconX() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}
