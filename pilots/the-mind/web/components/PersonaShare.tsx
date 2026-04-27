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

  const links: Array<{ label: string; href: string; icon: React.ReactNode }> = [
    {
      label: "X",
      href: `https://twitter.com/intent/tweet?text=${e(body)}&url=${e(url)}`,
      icon: <XIcon />,
    },
    {
      label: "LinkedIn",
      href: `https://www.linkedin.com/sharing/share-offsite/?url=${e(url)}`,
      icon: <LinkedInIcon />,
    },
    {
      label: "WhatsApp",
      href: `https://wa.me/?text=${e(body + " " + url)}`,
      icon: <WhatsAppIcon />,
    },
    {
      label: "Email",
      href: `mailto:?subject=${e(headline)}&body=${e(body + "\n\n" + url)}`,
      icon: <MailIcon />,
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
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 border border-parchment/15 hover:border-parchment/40 px-3 py-2 text-xs font-medium text-parchment/75 hover:text-parchment transition-colors"
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
