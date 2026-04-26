import type { Metadata } from "next";
import "./globals.css";
import PersonaSidebar from "@/components/PersonaSidebar";

export const metadata: Metadata = {
  title: "The Mind — Simulatte",
  description: "Simulate how real people think, decide, and react.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-screen bg-void text-parchment flex overflow-hidden">
        {/* Sidebar — desktop only */}
        <div className="hidden md:flex md:flex-shrink-0">
          <PersonaSidebar />
        </div>

        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
          {/* Mobile top nav */}
          <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-parchment/10 flex-shrink-0 bg-void">
            <a href="/" className="font-condensed font-bold text-parchment text-lg tracking-wide leading-none">
              The Mind
            </a>
            <a href="/generate" className="text-xs font-mono text-signal">
              + Generate
            </a>
          </div>

          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
