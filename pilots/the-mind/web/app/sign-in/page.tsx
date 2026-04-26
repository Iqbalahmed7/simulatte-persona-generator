"use client";

/**
 * app/sign-in/page.tsx — Sign-in page for The Mind.
 *
 * Two auth options:
 *   1. Google one-tap (primary)
 *   2. Resend magic link (email)
 *
 * Design: parchment text on void background, signal-green accents.
 * Shown on first visit to any gated route (/generate, /persona/*, /probe/*).
 */
import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

function SignInContent() {
  const params = useSearchParams();
  const callbackUrl = params.get("callbackUrl") ?? "/generate";
  const verify = params.get("verify") === "1";

  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleEmail(e: FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSending(true);
    setError(null);
    try {
      const res = await signIn("resend", {
        email: email.trim(),
        callbackUrl,
        redirect: false,
      });
      if (res?.error) {
        setError("Could not send the link. Check the address and try again.");
      } else {
        setSent(true);
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-10">
          <div className="font-condensed font-black text-parchment text-2xl tracking-wider uppercase leading-none">
            The Mind
          </div>
          <div className="font-mono text-parchment/40 text-[10px] tracking-widest mt-1">
            by Simulatte
          </div>
        </div>

        {verify ? (
          /* ── magic link sent state ── */
          <div className="space-y-4">
            <div className="w-2 h-2 bg-signal rounded-full" />
            <p className="text-parchment font-condensed font-bold text-xl">
              Check your inbox.
            </p>
            <p className="text-parchment/60 text-sm leading-relaxed">
              We sent a sign-in link to <span className="text-parchment">{email || "your email"}</span>.
              It expires in 10 minutes.
            </p>
            <p className="text-parchment/30 text-xs font-mono pt-2">
              No email? Check your spam folder, or try again.
            </p>
            <button
              onClick={() => { setSent(false); }}
              className="text-signal text-sm underline underline-offset-2 hover:text-signal/80 transition-colors"
            >
              Try a different address
            </button>
          </div>
        ) : sent ? (
          /* ── client-side sent confirmation ── */
          <div className="space-y-4">
            <div className="w-2 h-2 bg-signal rounded-full" />
            <p className="text-parchment font-condensed font-bold text-xl">
              Check your inbox.
            </p>
            <p className="text-parchment/60 text-sm leading-relaxed">
              We sent a sign-in link to <span className="text-parchment">{email}</span>.
              It expires in 10 minutes.
            </p>
          </div>
        ) : (
          <>
            <p className="text-parchment/60 text-sm leading-relaxed mb-8">
              Sign in to generate your own persona and run probes.
              Free — 1 persona, 3 probes, 5 chats per week.
            </p>

            {/* Google button */}
            <button
              onClick={() => signIn("google", { callbackUrl })}
              className="w-full flex items-center justify-center gap-3 bg-parchment/8 hover:bg-parchment/12 border border-parchment/15 text-parchment text-sm font-medium py-3 px-4 rounded transition-colors"
            >
              <GoogleIcon />
              Continue with Google
            </button>

            {/* Divider */}
            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-parchment/10" />
              <span className="text-parchment/30 text-xs font-mono tracking-widest">or</span>
              <div className="flex-1 h-px bg-parchment/10" />
            </div>

            {/* Email magic link */}
            <form onSubmit={handleEmail} className="space-y-3">
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
                className="w-full bg-parchment/5 border border-parchment/15 focus:border-signal/60 text-parchment placeholder-parchment/30 text-sm py-3 px-4 rounded outline-none transition-colors"
              />
              <button
                type="submit"
                disabled={sending || !email.trim()}
                className="w-full bg-signal hover:bg-signal/90 disabled:bg-signal/30 disabled:cursor-not-allowed text-void font-bold text-sm py-3 px-4 rounded transition-colors"
              >
                {sending ? "Sending…" : "Send sign-in link →"}
              </button>
              {error && (
                <p className="text-red-400/80 text-xs font-mono">{error}</p>
              )}
            </form>

            <p className="text-parchment/25 text-xs leading-relaxed mt-6">
              By signing in, you agree to simulate responsibly.
              No passwords stored — magic link only.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-void flex items-center justify-center">
        <div className="w-2 h-2 bg-signal/40 rounded-full animate-pulse" />
      </div>
    }>
      <SignInContent />
    </Suspense>
  );
}
