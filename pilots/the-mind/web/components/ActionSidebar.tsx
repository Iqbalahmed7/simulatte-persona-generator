/**
 * ActionSidebar — primary action rail on the dashboard.
 *
 * Desktop (lg+): vertical column on the left, 240px wide.
 * Mobile: horizontal scroll strip above main content.
 *
 * Two of the actions ("Ask a question", "Run a probe") need a persona,
 * so they open a PersonaPicker modal that lets the user pick from their
 * existing personas or kick off generation. "Generate" goes straight
 * to /generate.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import PersonaPicker, { PickerMode } from "./PersonaPicker";

interface MyPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
}

export default function ActionSidebar({
  personas,
  personasLeft,
}: {
  personas: MyPersona[];
  personasLeft: number;
}) {
  const [pickerMode, setPickerMode] = useState<PickerMode | null>(null);

  return (
    <>
      <p className="text-[10px] font-mono text-static uppercase tracking-[0.18em] mb-3">
        ACTIONS
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <ActionButton
          label="Generate persona"
          sub={personasLeft > 0 ? `${personasLeft} left this week` : "Resets Monday"}
          disabled={personasLeft === 0}
          href="/generate"
          icon={<IconUserPlus />}
        />
        <ActionButton
          label="Ask a question"
          sub="Chat with a persona"
          onClick={() => setPickerMode("chat")}
          icon={<IconChat />}
        />
        <ActionButton
          label="Run a probe"
          sub="Test product against persona"
          onClick={() => setPickerMode("probe")}
          icon={<IconProbe />}
        />
        <ActionButton
          label="Browse the wall"
          sub="Community personas"
          href="/community"
          icon={<IconWall />}
        />
      </div>

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

interface ActionButtonProps {
  label: string;
  sub: string;
  icon: React.ReactNode;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
}

function ActionButton(p: ActionButtonProps) {
  const cls =
    "block w-full text-left border border-parchment/10 hover:border-signal/40 hover:bg-parchment/[0.02] transition-colors p-4 group " +
    (p.disabled ? "opacity-40 cursor-not-allowed pointer-events-none" : "");
  const inner = (
    <div className="flex flex-col gap-3">
      <span className="text-parchment/60 group-hover:text-signal transition-colors">
        {p.icon}
      </span>
      <div className="min-w-0">
        <div className="font-condensed font-bold text-parchment text-sm leading-tight">
          {p.label}
        </div>
        <div className="font-mono text-[10px] text-parchment/50 tracking-wider uppercase mt-1 truncate">
          {p.sub}
        </div>
      </div>
    </div>
  );
  if (p.href) {
    return <Link href={p.href} className={cls}>{inner}</Link>;
  }
  return <button type="button" onClick={p.onClick} className={cls}>{inner}</button>;
}

// ── Icons ─────────────────────────────────────────────────────────────────
function IconUserPlus() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="7" cy="6" r="3" stroke="currentColor" strokeWidth="1.4" />
      <path d="M2 16c0-2.5 2-4 5-4s5 1.5 5 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M14 4v6M11 7h6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
function IconChat() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M3 4h12v8h-7l-4 3v-3H3z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}
function IconProbe() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="8" cy="8" r="5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M11.5 11.5L15 15" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
function IconWall() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect x="2" y="3" width="6" height="6" stroke="currentColor" strokeWidth="1.4" />
      <rect x="10" y="3" width="6" height="6" stroke="currentColor" strokeWidth="1.4" />
      <rect x="2" y="11" width="6" height="4" stroke="currentColor" strokeWidth="1.4" />
      <rect x="10" y="11" width="6" height="4" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
