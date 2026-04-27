/**
 * /welcome — public landing for users without an invite code.
 *
 * Shown when middleware sees no `invite_ok` cookie and no session. The page
 * explains The Mind is in private launch and invites visitors to request
 * access (mailto for now — can move to a form later) or paste a code.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function WelcomePage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      router.push(`/invite/${encodeURIComponent(code.trim())}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-void text-parchment flex flex-col">
      <header className="border-b border-parchment/10 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link href="/welcome" className="font-condensed font-black text-lg uppercase tracking-wider">
            The Mind
            <span className="ml-2 text-[10px] font-mono text-parchment/40 tracking-[0.18em]">
              BY SIMULATTE
            </span>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="max-w-2xl w-full">
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-4">
            PRIVATE LAUNCH · INVITE ONLY
          </p>
          <h1 className="font-condensed font-black text-5xl md:text-6xl leading-[0.96] mb-6">
            The decision <span className="text-signal">infrastructure</span> behind real consumer behaviour.
          </h1>
          <p className="text-parchment/72 text-lg leading-[1.78] mb-10 max-w-xl">
            The Mind is in a private cohort while we tune the simulation. If
            someone shared an invite code with you, enter it below.
          </p>

          <form onSubmit={onSubmit} className="flex flex-col sm:flex-row gap-3 mb-6">
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="INVITE CODE"
              className="flex-1 bg-transparent border border-parchment/20 px-4 py-3 font-mono text-sm tracking-widest text-parchment placeholder:text-parchment/30 focus:border-signal focus:outline-none"
              autoFocus
              autoComplete="off"
              spellCheck={false}
            />
            <button
              type="submit"
              disabled={submitting || !code.trim()}
              className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? "Checking…" : "Continue"}
            </button>
          </form>
          {error && (
            <p className="text-amber-400 text-sm font-mono mb-6">{error}</p>
          )}

          <div className="border-t border-parchment/10 pt-8">
            <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-3">
              NO CODE?
            </p>
            <p className="text-parchment/72 leading-[1.78]">
              Email{" "}
              <a
                href="mailto:mind@simulatte.io?subject=Request%20access%20to%20The%20Mind"
                className="text-signal underline underline-offset-4"
              >
                mind@simulatte.io
              </a>{" "}
              with one line on what you would test. We are letting people in
              every week.
            </p>
          </div>
        </div>
      </main>

      <footer className="border-t border-parchment/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <span className="text-[10px] font-mono text-parchment/40 tracking-[0.18em]">
            SIMULATTE · CONFIDENTIAL
          </span>
          <a
            href="https://simulatte.io"
            className="text-[10px] font-mono text-parchment/40 hover:text-signal tracking-[0.18em]"
          >
            SIMULATTE.IO
          </a>
        </div>
      </footer>
    </div>
  );
}
