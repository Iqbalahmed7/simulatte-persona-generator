/**
 * / — root entry.
 *
 * Server component that branches on auth:
 *   - Logged in → redirect to /dashboard (returning users skip marketing)
 *   - Anonymous → render the public marketing landing
 *
 * The marketing copy + sections live in components/MarketingLanding so
 * the file rename doesn't change anything that's been linked publicly.
 */
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import MarketingLanding from "@/components/MarketingLanding";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const session = await auth();
  if (session?.user) {
    redirect("/dashboard");
  }
  return <MarketingLanding />;
}
