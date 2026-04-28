"use client";

/**
 * PersonaShare.tsx — social-share row on the persona detail page.
 *
 * Five outlets: X / LinkedIn / WhatsApp / Email / Copy-link.
 * All use intent URLs (no SDKs, no third-party JS). The OG meta on the
 * shared URL — set in /persona/[id]/layout.tsx — handles the preview card.
 */
import { useState } from "react";

interface Props {
  personaId: string;
  name: string;
  age: number | null | undefined;
  city: string | null | undefined;
}

function siteOrigin(): string {
  if (typeof window !== "undefined") return window.location.origin;
  return "https://mind.simulatte.io";
}

function XIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}
function LinkedInIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.95v5.66H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.45zM5.34 7.43a2.06 2.06 0 11-.01-4.13 2.06 2.06 0 01.01 4.13zM7.12 20.45H3.56V9h3.56zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z" />
    </svg>
  );
}
function WhatsAppIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.198-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.71.306 1.263.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347zM12 2.04C6.5 2.04 2.04 6.5 2.04 12c0 1.755.46 3.402 1.27 4.838L2 22l5.27-1.382A9.94 9.94 0 0012 21.96c5.5 0 9.96-4.46 9.96-9.96S17.5 2.04 12 2.04z"/>
    </svg>
  );
}
function TelegramIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
    </svg>
  );
}
function SMSIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}
function MailIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="3" y="5" width="18" height="14" rx="1.5" />
      <path d="M3 7l9 6 9-6" />
    </svg>
  );
}
function LinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M10 13a5 5 0 007.07 0l3-3a5 5 0 10-7.07-7.07l-1.5 1.5" />
      <path d="M14 11a5 5 0 00-7.07 0l-3 3a5 5 0 107.07 7.07l1.5-1.5" />
    </svg>
  );
}

export default function PersonaShare({ personaId, name, age, city }: Props) {
  const [copied, setCopied] = useState(false);
  const url = `${siteOrigin()}/persona/${personaId}`;
  const meta = [age, city].filter(Boolean).join(", ");
  const headline = `Meet ${name || "this persona"}${meta ? `, ${meta}` : ""}.`;
  const body = `${headline} Simulated by The Mind — Simulatte's deep-persona engine.`;

  const e = encodeURIComponent;
  const message = `${body} ${url}`;

  // Native-app deeplinks (custom URL schemes) over web redirectors.
  // wa.me / linkedin.com/sharing land users on web sign-in or
  // download prompts when Universal Links don't fire (Brave, in-app
  // browsers, fresh sessions). Custom schemes hand off to the
  // installed app directly.
  //
  // `native: true` means the link opens in the same tab so iOS/Android
  // can resolve the scheme to the app. `target=_blank` actively breaks
  // this on iOS Safari + Brave.
  const links: Array<{
    label: string;
    href: string;
    icon: React.ReactNode;
    native?: boolean;
    onClick?: (e: React.MouseEvent<HTMLAnchorElement>) => void;
  }> = [
    {
      label: "WhatsApp",
      // whatsapp:// scheme opens the app on iOS/Android directly.
      href: `whatsapp://send?text=${e(message)}`,
      icon: <WhatsAppIcon />,
      native: true,
    },
    {
      label: "X",
      // twitter:// scheme opens X app on iOS; on desktop it falls back
      // to the web intent. We do device-based routing in onClick to
      // pick the right one without breaking either case.
      href: `https://twitter.com/intent/tweet?text=${e(body)}&url=${e(url)}`,
      icon: <XIcon />,
      onClick: (ev) => {
        if (typeof navigator !== "undefined" && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
          ev.preventDefault();
          // X iOS app handles twitter:// — message param, no URL slot.
          // We append the URL to the message body so it still gets shared.
          window.location.href = `twitter://post?message=${e(body + " " + url)}`;
        }
      },
      native: true,
    },
    {
      label: "LinkedIn",
      // LinkedIn killed reliable native share deeplinks. On mobile the
      // most useful action is: copy the share text + open the LI app
      // so the user can paste into a new post. On desktop, web share
      // works fine.
      href: `https://www.linkedin.com/sharing/share-offsite/?url=${e(url)}`,
      icon: <LinkedInIcon />,
      onClick: (ev) => {
        if (typeof navigator !== "undefined" && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
          ev.preventDefault();
          // Best-effort: copy compose text, then open LI app.
          navigator.clipboard?.writeText(message).catch(() => {});
          window.location.href = "linkedin://";
        }
      },
      native: true,
    },
    {
      label: "Telegram",
      // t.me uses Telegram Universal Links on iOS — opens the app.
      href: `https://t.me/share/url?url=${e(url)}&text=${e(body)}`,
      icon: <TelegramIcon />,
    },
    {
      label: "SMS",
      href: `sms:&body=${e(message)}`,
      icon: <SMSIcon />,
      native: true,
    },
    {
      label: "Email",
      href: `mailto:?subject=${e(headline)}&body=${e(body + "\n\n" + url)}`,
      icon: <MailIcon />,
      native: true,
    },
  ];

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch { /* clipboard unavailable */ }
  }

  return (
    <div className="border border-parchment/10 p-4 md:p-5">
      <p className="text-[10px] font-mono uppercase tracking-widest text-static mb-3">
        Share this persona
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {links.map((l) => (
          <a
            key={l.label}
            href={l.href}
            // Custom URL schemes (whatsapp://, sms:, mailto:, twitter://)
            // and Universal-Link share URLs MUST navigate same-tab so
            // iOS/Android can resolve them to the installed app. Adding
            // target=_blank shoves them into a popup tab where the OS
            // routing fails and falls back to web.
            target={l.native ? undefined : "_blank"}
            rel={l.native ? undefined : "noopener noreferrer"}
            onClick={l.onClick}
            className="inline-flex items-center gap-2 border border-parchment/15 hover:border-parchment/40 px-3 py-2 text-xs font-medium text-parchment/75 hover:text-parchment transition-colors"
            style={{ minHeight: 44 }}
            aria-label={`Share on ${l.label}`}
          >
            <span className="text-parchment/60">{l.icon}</span>
            {l.label}
          </a>
        ))}
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-2 border border-parchment/15 hover:border-parchment/40 px-3 py-2 text-xs font-medium text-parchment/75 hover:text-parchment transition-colors"
          aria-label="Copy link"
        >
          <span className="text-parchment/60">
            {copied ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12l5 5L20 7" /></svg>
            ) : <LinkIcon />}
          </span>
          {copied ? "Copied" : "Copy link"}
        </button>
      </div>
      <p className="text-[10px] font-mono text-static mt-3 leading-relaxed">
        Anyone with the link can view this persona — chat and probes still
        require sign-in.
      </p>
    </div>
  );
}
