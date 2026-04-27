"use client";

/**
 * TurnstileWidget — Cloudflare Turnstile bot challenge.
 *
 * Renders the invisible/managed widget. Calls onVerified(token) on success.
 * If NEXT_PUBLIC_TURNSTILE_SITE_KEY is unset, calls onVerified("") immediately
 * (dev mode — backend also no-ops if TURNSTILE_SECRET is unset).
 */
import { useEffect, useRef } from "react";

interface Props {
  onVerified: (token: string) => void;
  theme?: "light" | "dark" | "auto";
}

declare global {
  interface Window {
    turnstile?: {
      render: (el: HTMLElement, opts: Record<string, unknown>) => string;
      reset: (id?: string) => void;
    };
    onTurnstileLoad?: () => void;
  }
}

const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "";

export default function TurnstileWidget({ onVerified, theme = "dark" }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!SITE_KEY) {
      // Dev / unconfigured — auto-verify so flow isn't blocked.
      onVerified("");
      return;
    }
    let cancelled = false;

    function render() {
      if (cancelled || !ref.current || !window.turnstile) return;
      if (widgetIdRef.current) return;
      widgetIdRef.current = window.turnstile.render(ref.current, {
        sitekey: SITE_KEY,
        theme,
        callback: (token: string) => onVerified(token),
        "error-callback": () => onVerified(""),
        "expired-callback": () => onVerified(""),
      });
    }

    if (window.turnstile) {
      render();
    } else {
      const existing = document.querySelector<HTMLScriptElement>("#cf-turnstile-script");
      if (!existing) {
        const s = document.createElement("script");
        s.id = "cf-turnstile-script";
        s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad";
        s.async = true;
        s.defer = true;
        document.head.appendChild(s);
      }
      window.onTurnstileLoad = render;
    }
    return () => { cancelled = true; };
  }, [onVerified, theme]);

  if (!SITE_KEY) return null;
  return <div ref={ref} />;
}
