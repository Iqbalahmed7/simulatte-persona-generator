/**
 * NavRail — collapsible left nav rail for authed surfaces.
 *
 * Expanded: 240px, full labels.
 * Collapsed: 64px, icons only.
 * State persists in localStorage `mind:nav:collapsed`.
 *
 * Hidden below md — mobile users get the existing TopNav + their
 * primary actions land in the page body.
 *
 * Two of the actions need a persona ("Ask a question", "Run a probe")
 * so they open the existing PersonaPicker modal. "Generate" links to
 * /generate, "Browse the wall" links to /community.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import PersonaPicker, { PickerMode } from "./PersonaPicker";

interface MyPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
  occupation?: string;
  snippet?: string;
}

const COLLAPSED_KEY = "mind:nav:collapsed";

async function doSignOut() {
  try {
    const csrfRes = await fetch("/api/auth/csrf", { cache: "no-store" });
    const { csrfToken } = await csrfRes.json();
    const form = new FormData();
    form.append("csrfToken", csrfToken);
    form.append("callbackUrl", "/welcome");
    await fetch("/api/auth/signout", { method: "POST", body: form });
  } finally {
    window.location.href = "/welcome";
  }
}

export default function NavRail({
  personas,
  personasLeft,
  isAdmin = false,
}: {
  personas: MyPersona[];
  personasLeft: number;
  isAdmin?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [pickerMode, setPickerMode] = useState<PickerMode | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(COLLAPSED_KEY) === "1");
    } catch {}
  }, []);

  const toggle = () => {
    setCollapsed((c) => {
      const next = !c;
      try { localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0"); } catch {}
      return next;
    });
  };

  const width = collapsed ? 64 : 240;

  return (
    <>
      <aside
        className="hidden md:flex flex-col border-r border-parchment/10 bg-void sticky top-0 self-start h-screen flex-shrink-0 transition-[width] duration-200 ease-out"
        style={{ width }}
      >
        {/* Brand */}
        <div className={"flex items-center px-4 py-5 border-b border-parchment/5 " + (collapsed ? "justify-center" : "gap-3")}>
          <Link href="/dashboard" className="flex items-center gap-3">
            <EngineMark size={26} />
            {!collapsed && (
              <span className="font-condensed font-black text-parchment text-base uppercase tracking-wider whitespace-nowrap">
                The Mind
              </span>
            )}
          </Link>
        </div>

        {/* Primary actions */}
        <nav className="flex-1 flex flex-col py-4 gap-1 overflow-y-auto">
          {!collapsed && (
            <p className="text-[10px] font-mono text-static uppercase tracking-[0.18em] px-4 mb-2">
              Actions
            </p>
          )}
          <RailItem
            collapsed={collapsed}
            href="/generate"
            label="Generate persona"
            sub={personasLeft > 0 ? `${personasLeft} left this week` : "Resets Monday"}
            active={pathname === "/generate"}
            icon={<IconUserPlus />}
          />
          <RailItem
            collapsed={collapsed}
            label="Ask a question"
            sub="Chat with a persona"
            onClick={() => setPickerMode("chat")}
            icon={<IconChat />}
          />
          <RailItem
            collapsed={collapsed}
            label="Run a probe"
            sub="Test product fit"
            onClick={() => setPickerMode("probe")}
            icon={<IconProbe />}
          />
          <RailItem
            collapsed={collapsed}
            href="/community"
            label="Browse the wall"
            sub="Community personas"
            active={pathname === "/community"}
            icon={<IconWall />}
          />

          <div className="flex-1" />

          {/* Secondary / utility */}
          {!collapsed && (
            <p className="text-[10px] font-mono text-static uppercase tracking-[0.18em] px-4 mt-2 mb-2">
              Account
            </p>
          )}
          <RailItem
            collapsed={collapsed}
            href="/dashboard"
            label="Dashboard"
            active={pathname === "/dashboard"}
            icon={<IconHome />}
          />
          {isAdmin && (
            <RailItem
              collapsed={collapsed}
              href="/admin"
              label="Admin"
              active={pathname?.startsWith("/admin") ?? false}
              icon={<IconAdmin />}
            />
          )}
          <RailButton collapsed={collapsed} label="Sign out" onClick={doSignOut} icon={<IconSignOut />} />
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={toggle}
          aria-label={collapsed ? "Expand nav" : "Collapse nav"}
          className="border-t border-parchment/5 px-4 py-3 text-[10px] font-mono text-static hover:text-signal uppercase tracking-[0.18em] flex items-center justify-center gap-2"
        >
          {collapsed ? "›" : "‹  Collapse"}
        </button>
      </aside>

      {pickerMode && (
        <PersonaPicker
          mode={pickerMode}
          personas={personas}
          onClose={() => setPickerMode(null)}
        />
      )}
    </>
  );
}

function RailItem({
  collapsed,
  href,
  label,
  sub,
  active,
  onClick,
  icon,
}: {
  collapsed: boolean;
  href?: string;
  label: string;
  sub?: string;
  active?: boolean;
  onClick?: () => void;
  icon: React.ReactNode;
}) {
  const className =
    "flex items-center gap-3 px-4 py-2.5 text-left transition-colors " +
    (active
      ? "text-signal border-l-2 border-signal bg-parchment/[0.02]"
      : "text-parchment/85 hover:text-parchment hover:bg-parchment/[0.03] border-l-2 border-transparent");

  const content = (
    <>
      <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center text-current">
        {icon}
      </span>
      {!collapsed && (
        <span className="flex-1 min-w-0">
          <span className="block text-[13px] font-sans leading-tight truncate">{label}</span>
          {sub && (
            <span className="block text-[10px] font-mono text-static uppercase tracking-widest truncate mt-0.5">
              {sub}
            </span>
          )}
        </span>
      )}
    </>
  );

  if (href) {
    return (
      <Link href={href} className={className} title={collapsed ? label : undefined}>
        {content}
      </Link>
    );
  }
  return (
    <button onClick={onClick} className={className} title={collapsed ? label : undefined}>
      {content}
    </button>
  );
}

function RailButton(props: {
  collapsed: boolean;
  label: string;
  onClick: () => void;
  icon: React.ReactNode;
}) {
  return <RailItem {...props} />;
}

function EngineMark({ size: s = 32 }: { size?: number }) {
  return (
    <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
      <path d="M 10,26.392 A 12,12 0 1 0 10,5.608" stroke="#E9E6DF" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M 12.5,22.062 A 7,7 0 1 0 12.5,9.938" stroke="#E9E6DF" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="16" cy="16" r="3" fill="#A8FF3E" />
    </svg>
  );
}

function IconUserPlus() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="9" cy="8" r="3.5" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M18 8v6M15 11h6" strokeLinecap="round" />
    </svg>
  );
}
function IconChat() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 5h16v11H8l-4 3z" strokeLinejoin="round" />
    </svg>
  );
}
function IconProbe() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="11" cy="11" r="6" />
      <path d="M16 16l5 5" strokeLinecap="round" />
    </svg>
  );
}
function IconWall() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="4" width="7" height="7" />
      <rect x="14" y="4" width="7" height="7" />
      <rect x="3" y="14" width="7" height="6" />
      <rect x="14" y="14" width="7" height="6" />
    </svg>
  );
}
function IconHome() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" strokeLinejoin="round" />
    </svg>
  );
}
function IconSignOut() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" strokeLinejoin="round" />
      <path d="M16 8l4 4-4 4M20 12H10" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconAdmin() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M12 3l8 4v5c0 5-3.4 8.5-8 9-4.6-.5-8-4-8-9V7z" strokeLinejoin="round" />
    </svg>
  );
}
