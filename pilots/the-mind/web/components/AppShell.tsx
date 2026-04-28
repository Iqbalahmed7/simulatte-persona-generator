/**
 * AppShell — three-column layout for authed dashboard surfaces.
 *
 *   ┌──────────┬──────────────────────┬───────────┐
 *   │ NavRail  │ children (center)    │ WallTicker │
 *   │ 240/64px │ flex-1 max-w-3xl-ish │ 320px      │
 *   └──────────┴──────────────────────┴───────────┘
 *
 * Below md: NavRail hidden, content full-width.
 * Below lg: WallTicker hidden.
 *
 * Currently mounted only on /dashboard. Other authed pages can adopt
 * it incrementally — same shell, different center.
 */
"use client";

import NavRail from "./NavRail";
import WallTicker from "./WallTicker";

interface MyPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
}

export default function AppShell({
  personas,
  personasLeft,
  isAdmin = false,
  children,
}: {
  personas: MyPersona[];
  personasLeft: number;
  isAdmin?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-void text-parchment">
      <NavRail personas={personas} personasLeft={personasLeft} isAdmin={isAdmin} />
      <main className="flex-1 min-w-0">{children}</main>
      <WallTicker />
    </div>
  );
}
