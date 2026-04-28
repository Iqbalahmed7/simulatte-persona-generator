/**
 * MobileBottomNav — sticky bottom action bar for phones.
 *
 * Mobile is the go-to screen for The Mind, so the four primary verbs
 * (Dashboard / Ask / Probe / Build) must always be one tap away,
 * regardless of which page you're on. Mounted in app/layout so every
 * authed route gets it; auto-hides on auth/marketing routes.
 *
 * - 64px row + env(safe-area-inset-bottom) for the iPhone home bar.
 * - Generate is the visual focus (signal-green) — that's the moneymaker.
 * - md:hidden — desktop has the NavRail.
 *
 * Pages that mount this should add `pb-28 sm:pb-0` (or equivalent
 * safe-area-inset bottom padding) on their outermost main element so
 * content doesn't hide behind the bar.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Routes where the bar should NOT appear: marketing/auth/onboarding.
const HIDE_ON_PREFIX = ["/welcome", "/sign-in", "/invite", "/privacy", "/terms"];

export default function MobileBottomNav() {
  const pathname = usePathname() ?? "/";

  // Hide on marketing/auth/onboarding routes — the bar is for authed app pages.
  const hidden =
    pathname === "/" ||
    HIDE_ON_PREFIX.some((p) => pathname === p || pathname.startsWith(p + "/"));

  if (hidden) return null;

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-void/95 backdrop-blur-md border-t border-parchment/15"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      aria-label="Primary actions"
    >
      <div className="flex">
        <NavItem href="/dashboard" active={isActive(pathname, "/dashboard")} label="Home" icon={<IconHome />} />
        <NavItem href="/community" active={isActive(pathname, "/community")} label="Wall" icon={<IconWall />} />
        <NavItem
          href="/generate"
          active={isActive(pathname, "/generate")}
          label="Build"
          icon={<IconBuild />}
          accent
        />
      </div>
    </nav>
  );
}

function isActive(path: string, prefix: string): boolean {
  if (prefix === "/dashboard") return path === "/dashboard";
  return path === prefix || path.startsWith(prefix + "/");
}

function NavItem({
  href,
  label,
  icon,
  active,
  accent = false,
}: {
  href: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
  accent?: boolean;
}) {
  const color = accent
    ? "text-signal"
    : active
    ? "text-parchment"
    : "text-parchment/55";
  return (
    <Link
      href={href}
      className={
        "flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-colors " +
        color
      }
      style={{ minHeight: 56 }}
    >
      <span className="block">{icon}</span>
      <span className="text-[10px] font-mono uppercase tracking-[0.16em]">
        {label}
      </span>
    </Link>
  );
}

/* ────────────────────────── icons ────────────────────────── */

function IconHome() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1v-9z" strokeLinejoin="round" />
    </svg>
  );
}

function IconWall() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="4" width="7" height="7" />
      <rect x="14" y="4" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
    </svg>
  );
}

function IconBuild() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v10M7 12h10" strokeLinecap="round" />
    </svg>
  );
}
