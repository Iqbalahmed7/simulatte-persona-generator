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
        <PersonaSidebar />
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </body>
    </html>
  );
}
