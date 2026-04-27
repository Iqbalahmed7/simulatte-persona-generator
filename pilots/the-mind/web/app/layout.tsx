/**
 * Root layout. Intentionally minimal: no persistent chrome.
 *
 * The legacy PersonaSidebar + mobile top-nav that used to live here
 * have been removed because they were appearing on every page (including
 * the new /dashboard) and visually competing with the new TopNav +
 * ActionSidebar. Each page now owns its own header — /dashboard mounts
 * <TopNav>, /welcome and /invite have their own minimal headers, and
 * /persona/[id] / /generate keep theirs.
 *
 * AllowanceProvider stays because AllowanceCounter (still used on a
 * couple of pages) reads from its context.
 */
import type { Metadata } from "next";
import "./globals.css";
import AllowanceProvider from "@/components/AllowanceProvider";

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
      <body className="bg-void text-parchment min-h-screen">
        <AllowanceProvider>
          {children}
        </AllowanceProvider>
      </body>
    </html>
  );
}
