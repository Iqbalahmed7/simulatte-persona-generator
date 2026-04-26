import type { Metadata } from "next";
import "./globals.css";
import PersonaSidebar from "@/components/PersonaSidebar";
import AllowanceProvider from "@/components/AllowanceProvider";
import AllowanceCounter from "@/components/AllowanceCounter";

export const metadata: Metadata = {
  metadataBase: new URL("https://mind.simulatte.io"),
  title: "The Mind — Simulatte",
  description: "Talk to a person who doesn't exist. The Mind generates a behaviourally coherent synthetic person from a brief paragraph, then lets you simulate any decision they'd make.",
  icons: {
    icon: "/favicon.svg",
    apple: "/apple-touch-icon.svg",
  },
  openGraph: {
    title: "The Mind — Simulatte",
    description: "Talk to a person who doesn't exist. Simulate how real people think, decide, and react.",
    url: "https://mind.simulatte.io",
    siteName: "The Mind",
    images: [
      {
        url: "/og-image.svg",
        width: 1200,
        height: 630,
        alt: "The Mind by Simulatte",
      },
    ],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "The Mind — Simulatte",
    description: "Talk to a person who doesn't exist. Simulate decisions.",
    images: ["/og-image.svg"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-screen bg-void text-parchment flex overflow-hidden">
        <AllowanceProvider>
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
              <div className="flex items-center gap-4">
                <AllowanceCounter />
                <a href="/generate" className="text-xs font-mono text-signal">
                  + Generate
                </a>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {children}
            </div>
          </div>
        </AllowanceProvider>
      </body>
    </html>
  );
}
