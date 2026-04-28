/**
 * GET /api/me — same-origin proxy to FastAPI's /me.
 *
 * AccessGate was fetching the cross-origin API URL directly, which gets
 * blocked by Brave Shields and similar content blockers (same root cause
 * as the /redeem-code "Failed to fetch" issue). This proxy reads the
 * Auth.js session server-side, mints the same HS256 JWT we use elsewhere,
 * and forwards the call. The browser only sees a same-origin GET.
 */
import { auth } from "@/auth";
import { SignJWT } from "jose";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

export async function GET() {
  const session = await auth();
  const user = session?.user as { id?: string; email?: string } | undefined;
  if (!user?.email) {
    return new Response(JSON.stringify({ detail: "not_authenticated" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }
  const secret = process.env.NEXTAUTH_SECRET ?? "";
  const token = await new SignJWT({ sub: user.id, email: user.email })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(new TextEncoder().encode(secret));

  const upstream = await fetch(`${API}/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      // Browser-cache for 15s. AccessGate, DashboardHome, and
      // ReferralLauncher all fetch /api/me on dashboard load — without
      // this they each hit Railway (cold-start ~300-600ms × 3). With
      // private,max-age=15 the second/third callers reuse the browser
      // cache, and a same-tab refresh within 15s skips the round-trip.
      "cache-control": "private, max-age=15, stale-while-revalidate=60",
    },
  });
}
