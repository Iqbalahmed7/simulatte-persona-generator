/**
 * track — thin Plausible wrapper.
 *
 * Plausible's script is loaded conditionally in app/layout.tsx when
 * NEXT_PUBLIC_PLAUSIBLE_DOMAIN is set (currently mind.simulatte.io).
 * When the script is present, it exposes `window.plausible` as a
 * global function. When it isn't (local dev, env var unset), this is
 * a no-op — never throws, never breaks the UI.
 *
 * Usage:
 *   import { track } from "@/lib/track";
 *   track("share", { app: "whatsapp", surface: "persona" });
 *
 * Privacy: Plausible is cookie-less, GDPR-friendly. We only send
 * low-cardinality strings (app name, surface name) — no PII.
 */
type PlausibleProps = Record<string, string | number | boolean>;

declare global {
  interface Window {
    plausible?: (event: string, options?: { props?: PlausibleProps }) => void;
  }
}

export function track(event: string, props?: PlausibleProps): void {
  if (typeof window === "undefined") return;
  try {
    window.plausible?.(event, props ? { props } : undefined);
  } catch {
    // Never let analytics break the app.
  }
}
