/**
 * TopNav — site-wide navigation for authed users.
 *
 * Mobile-first: collapses to a hamburger below md. Logo + main nav left,
 * email + sign-out right. Admins see an extra Admin link.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { signOut, useSession } from "next-auth/react";

function MindMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M 10,26.392 A 12,12 0 1 0 10,5.608" stroke="#E9E6DF" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M 12.5,22.062 A 7,7 0 1 0 12.5,9.938" stroke="#E9E6DF" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="16" cy="16" r="3" fill="#A8FF3E" />
    </svg>
  );
}

export default function TopNav({ isAdmin = false }: { isAdmin?: boolean }) {
  const { data: session } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);
  const email = session?.user?.email ?? "";

  const links = (
    <>
      <Link href="/dashboard" className="text-parchment/70 hover:text-signal text-sm tracking-wide">Home</Link>
      <Link href="/generate" className="text-parchment/70 hover:text-signal text-sm tracking-wide">Build</Link>
      <Link href="/community" className="text-parchment/70 hover:text-signal text-sm tracking-wide">Wall</Link>
      {isAdmin && (
        <Link href="/admin" className="text-parchment/70 hover:text-signal text-sm tracking-wide">Admin</Link>
      )}
    </>
  );

  return (
    <header className="border-b border-parchment/10 bg-void">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
        {/* Left: logo + desktop nav */}
        <div className="flex items-center gap-6 min-w-0">
          <Link href="/dashboard" className="flex items-center gap-2 flex-shrink-0">
            <MindMark size={24} />
            <span className="font-condensed font-black text-parchment text-base tracking-wider uppercase">
              Mind
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-5">
            {links}
          </nav>
        </div>

        {/* Right: email + sign-out (desktop), hamburger (mobile) */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMenuOpen((m) => !m)}
            className="md:hidden text-parchment/70 hover:text-signal p-1"
            aria-label="Open menu"
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              {menuOpen ? (
                <path d="M5 5L17 17M17 5L5 17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              ) : (
                <>
                  <path d="M3 6h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M3 11h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M3 16h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </>
              )}
            </svg>
          </button>
          <div className="hidden md:flex items-center gap-3 min-w-0">
            <span className="font-mono text-[11px] text-parchment/50 truncate max-w-[180px] lg:max-w-[260px]">
              {email}
            </span>
            <button
              type="button"
              onClick={() => signOut({ callbackUrl: "/welcome" })}
              className="text-[10px] font-mono uppercase tracking-widest text-parchment/60 hover:text-signal"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu drawer */}
      {menuOpen && (
        <div className="md:hidden border-t border-parchment/10 px-4 py-4 space-y-3">
          <div className="flex flex-col gap-3">{links}</div>
          <div className="pt-3 border-t border-parchment/10">
            <p className="font-mono text-[11px] text-parchment/50 truncate mb-2">{email}</p>
            <button
              type="button"
              onClick={() => signOut({ callbackUrl: "/welcome" })}
              className="text-[10px] font-mono uppercase tracking-widest text-parchment/60 hover:text-signal"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
