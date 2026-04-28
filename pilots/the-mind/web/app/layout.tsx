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
import type { Metadata, Viewport } from "next";
import Script from "next/script";
import Link from "next/link";
import "./globals.css";
import AllowanceProvider from "@/components/AllowanceProvider";
import MobileBottomNav from "@/components/MobileBottomNav";

// Plausible Analytics — loaded only if NEXT_PUBLIC_PLAUSIBLE_DOMAIN is
// set. Privacy-respecting, cookie-less, no PII. Set the env var to
// "mind.simulatte.io" on Vercel to turn it on.
const PLAUSIBLE_DOMAIN = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;

export const metadata: Metadata = {
  metadataBase: new URL("https://mind.simulatte.io"),
  title: "The Mind — Simulatte",
  description: "Talk to a person who doesn't exist. The Mind generates a behaviourally coherent synthetic person from a brief paragraph, then lets you simulate any decision they'd make.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    title: "The Mind",
    statusBarStyle: "black-translucent",
    capable: true,
  },
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

export const viewport: Viewport = {
  themeColor: "#050505",
  // viewportFit=cover lets us paint into the iPhone notch / home-bar
  // area; pages still respect env(safe-area-inset-*) for content.
  viewportFit: "cover",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {PLAUSIBLE_DOMAIN && (
          <Script
            defer
            data-domain={PLAUSIBLE_DOMAIN}
            src="https://plausible.io/js/script.js"
            strategy="afterInteractive"
          />
        )}
      </head>
      <body className="bg-void text-parchment min-h-screen">
        <AllowanceProvider>
          {children}
        </AllowanceProvider>
        <footer
          className="border-t border-parchment/10 mt-16 py-6 text-center text-[10px] font-mono uppercase tracking-[0.18em] text-static/70"
          style={{ paddingBottom: "calc(1.5rem + env(safe-area-inset-bottom, 0px))" }}
        >
          <Link href="/privacy" className="hover:text-signal mx-3">Privacy</Link>
          <span className="text-parchment/20">·</span>
          <Link href="/terms" className="hover:text-signal mx-3">Terms</Link>
          <span className="text-parchment/20">·</span>
          <a href="mailto:mind@simulatte.io" className="hover:text-signal mx-3">Contact</a>
        </footer>
        {/* Sticky mobile-only action bar — primary verbs always one tap
            away. Hidden on marketing/auth routes via internal pathname
            check; hidden on md+ via Tailwind. */}
        <MobileBottomNav />
      </body>
    </html>
  );
}
