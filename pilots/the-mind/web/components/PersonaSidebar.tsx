"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { fetchGeneratedList, GeneratedPersonaSummary } from "@/lib/api";

export default function PersonaSidebar() {
  const pathname = usePathname();
  const [personas, setPersonas] = useState<GeneratedPersonaSummary[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    const list = await fetchGeneratedList();
    setPersonas(list);
  }, []);

  useEffect(() => {
    load();
    intervalRef.current = setInterval(load, 30_000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [load]);

  // Refresh immediately when navigating (catches freshly generated personas)
  useEffect(() => { load(); }, [pathname, load]);

  const activeId = pathname.startsWith("/persona/") ? pathname.split("/persona/")[1] : null;

  return (
    <aside
      className={`flex-shrink-0 flex flex-col border-r border-parchment/10 bg-void transition-all duration-200
        ${collapsed ? "w-10" : "w-56"}`}
      style={{ minHeight: "100vh" }}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-3 py-4 border-b border-parchment/10">
        {!collapsed && (
          <span className="text-[10px] font-sans font-semibold tracking-widest uppercase text-static">
            Personas
          </span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="text-static hover:text-parchment/60 transition-colors ml-auto"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <span className="font-mono text-xs">{collapsed ? "›" : "‹"}</span>
        </button>
      </div>

      {!collapsed && (
        <>
          {/* Generate button */}
          <div className="px-3 py-3 border-b border-parchment/10">
            <Link
              href="/generate"
              className="flex items-center gap-2 text-[11px] font-mono text-signal hover:text-parchment transition-colors"
            >
              <span className="text-base leading-none">+</span>
              <span>Generate</span>
            </Link>
          </div>

          {/* Persona list */}
          <div className="flex-1 overflow-y-auto py-2">
            {personas.length === 0 ? (
              <p className="px-3 py-4 text-[10px] font-mono text-static leading-relaxed">
                No generated personas yet.
                <br />Generate your first one →
              </p>
            ) : (
              personas.map((p) => {
                const isActive = p.persona_id === activeId;
                return (
                  <Link
                    key={p.persona_id}
                    href={`/persona/${p.persona_id}`}
                    className={`block px-3 py-3 border-b border-parchment/5 transition-colors
                      ${isActive
                        ? "bg-parchment/5 border-l-2 border-l-signal"
                        : "hover:bg-parchment/5 border-l-2 border-l-transparent"}`}
                  >
                    <p className={`text-xs font-medium truncate ${isActive ? "text-parchment" : "text-parchment/80"}`}>
                      {p.name}
                    </p>
                    <p className="text-[10px] font-mono text-static truncate mt-0.5">
                      {p.age} · {p.city || p.country}
                    </p>
                    {p.brief_snippet && (
                      <p className="text-[10px] text-parchment/40 mt-1 line-clamp-2 leading-snug">
                        {p.brief_snippet}
                      </p>
                    )}
                  </Link>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-3 border-t border-parchment/10">
            <span className="font-mono text-[9px] text-static">mind.simulatte.io</span>
          </div>
        </>
      )}
    </aside>
  );
}
