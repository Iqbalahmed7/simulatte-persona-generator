/**
 * /admin/* layout — gates the entire admin tree behind the email allowlist.
 *
 * Reads ADMIN_EMAILS env var (comma-separated). If the signed-in user's
 * email isn't on the list, returns a hard 404 — no leakage of the admin
 * route's existence.
 */
import { notFound } from "next/navigation";
import Link from "next/link";
import { getAdminUser } from "@/lib/admin";

export const dynamic = "force-dynamic";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const admin = await getAdminUser();
  if (!admin) notFound();

  return (
    <div className="min-h-screen bg-void text-parchment">
      <header className="border-b border-parchment/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-baseline justify-between gap-6">
          <div className="flex items-baseline gap-6">
            <Link href="/admin" className="font-condensed font-black text-lg uppercase tracking-wider">
              Mind / Admin
            </Link>
            <nav className="flex gap-4 text-xs font-mono uppercase tracking-widest">
              <Link href="/admin" className="text-parchment/60 hover:text-signal">Stats</Link>
              <Link href="/admin/users" className="text-parchment/60 hover:text-signal">Users</Link>
              <Link href="/admin/personas" className="text-parchment/60 hover:text-signal">Personas</Link>
              <Link href="/admin/probes" className="text-parchment/60 hover:text-signal">Probes</Link>
              <Link href="/admin/events" className="text-parchment/60 hover:text-signal">Events</Link>
              <Link href="/admin/invites" className="text-parchment/60 hover:text-signal">Invites</Link>
              <Link href="/admin/access-requests" className="text-parchment/60 hover:text-signal">Access</Link>
              <Link href="/admin/referrals" className="text-parchment/60 hover:text-signal">Referrals</Link>
              <Link href="/admin/flagged" className="text-amber-400/70 hover:text-amber-400">Flagged</Link>
            </nav>
          </div>
          <span className="text-[10px] font-mono text-parchment/40">
            {admin.email}
          </span>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
