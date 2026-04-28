/**
 * MobileActionGrid — 2x2 grid of primary CTAs for mobile screens.
 *
 * On desktop the same actions live in NavRail; on mobile NavRail is
 * hidden so we surface them inline at the top of the dashboard center
 * column. Visible only below md.
 *
 * Tap targets are 64px+ tall to satisfy WCAG / Apple HIG (44pt) with
 * margin to spare. Two-of-the-four open the PersonaPicker modal.
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
  occupation?: string;
  snippet?: string;
}

export default function MobileActionGrid({
  personas,
  personasLeft,
}: {
  personas: MyPersona[];
  personasLeft: number;
}) {
  const [pickerMode, setPickerMode] = useState<PickerMode | null>(null);

  return (
    <>
      <div className="md:hidden grid grid-cols-2 gap-3">
        <Tile
          href="/generate"
          label="Generate"
          sub={personasLeft > 0 ? `${personasLeft} left` : "Resets Mon"}
          accent
        />
        <Tile
          onClick={() => setPickerMode("chat")}
          label="Ask"
          sub="Chat with persona"
        />
        <Tile
          onClick={() => setPickerMode("probe")}
          label="Probe"
          sub="Test your product"
        />
        <Tile
          href="/community"
          label="The wall"
          sub="Community personas"
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

function Tile({
  href,
  onClick,
  label,
  sub,
  accent,
}: {
  href?: string;
  onClick?: () => void;
  label: string;
  sub: string;
  accent?: boolean;
}) {
  const className =
    "flex flex-col justify-between p-4 min-h-[88px] border transition-colors text-left active:opacity-80 " +
    (accent
      ? "bg-signal text-void border-signal"
      : "border-parchment/15 text-parchment hover:border-signal/40");

  const content = (
    <>
      <span className="font-condensed font-bold uppercase tracking-wider text-base">
        {label}
      </span>
      <span
        className={
          "font-mono text-[10px] tracking-widest uppercase " +
          (accent ? "text-void/70" : "text-static")
        }
      >
        {sub}
      </span>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={className}>
        {content}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={className}>
      {content}
    </button>
  );
}
