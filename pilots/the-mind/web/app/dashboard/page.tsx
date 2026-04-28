/**
 * /dashboard — authed user home.
 *
 * Server component checks the session; if not signed in redirects to
 * /welcome. Renders TopNav + DashboardHome (a client component that
 * pulls /me + /me/personas with the HS256 token).
 */
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { SignJWT } from "jose";
import TopNav from "@/components/TopNav";
import DashboardHome from "@/components/DashboardHome";
import AccessGate from "@/components/AccessGate";
import FeedbackModal from "@/components/FeedbackModal";

export const dynamic = "force-dynamic";

const ADMIN_EMAILS = new Set(
  (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)
);

async function mintToken(user: { id?: string; email?: string }): Promise<string> {
  const secret = process.env.NEXTAUTH_SECRET ?? "";
  return await new SignJWT({ sub: user.id, email: user.email })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("15m")
    .sign(new TextEncoder().encode(secret));
}

export default async function DashboardPage() {
  const session = await auth();
  const user = session?.user as { id?: string; email?: string; name?: string } | undefined;
  if (!user?.id) {
    redirect("/welcome");
  }
  const token = await mintToken(user);
  const isAdmin = ADMIN_EMAILS.has((user.email ?? "").toLowerCase());

  return (
    <AccessGate>
      {/* TopNav is mobile-only — desktop gets the new collapsible NavRail
          inside <AppShell> via DashboardHome. */}
      <div className="md:hidden">
        <TopNav isAdmin={isAdmin} email={user.email ?? ""} />
      </div>
      <DashboardHome authToken={token} isAdmin={isAdmin} />
      {!isAdmin && <FeedbackModal surface="general" />}
    </AccessGate>
  );
}
