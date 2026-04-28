/**
 * POST /api/redeem-code — same-origin proxy to FastAPI's /redeem-code.
 *
 * Why: the auto-redeem flow on the Waitlist screen was getting "Failed
 * to fetch" against the cross-origin API URL — Brave Shields, ad-block
 * extensions, and some corporate proxies block the third-party request.
 * Routing through this same-origin handler sidesteps all of it.
 *
 * Auth: reads the Auth.js session, mints a short-lived JWT keyed off
 * NEXTAUTH_SECRET (same scheme as adminPost in lib/admin.ts), and
 * forwards it as a Bearer token. The browser doesn't see the API URL
 * or the token.
 */
import { auth } from "@/auth";
import { SignJWT } from "jose";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

export async function POST(request: Request) {
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

  const body = await request.text(); // pass through { code } payload as-is
  const upstream = await fetch(`${API}/redeem-code`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body,
    cache: "no-store",
  });
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
