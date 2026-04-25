import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Mind — Simulatte",
  description: "Simulate how real people think, decide, and react.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-void text-parchment">{children}</body>
    </html>
  );
}
