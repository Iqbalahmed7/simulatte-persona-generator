/**
 * GET /api/token — mint a short-lived HS256 JWT for the FastAPI backend.
 *
 * Why this exists:
 *   The Auth.js session cookie is httpOnly + JWE-encrypted, so neither
 *   document.cookie nor FastAPI can read it directly. This endpoint runs
 *   server-side (Node runtime), uses auth() to verify the session via the
 *   httpOnly cookie, then mints a plain HS256 JWT containing user.id and
 *   user.email, signed with NEXTAUTH_SECRET — which the FastAPI backend
 *   already knows how to verify.
 */
import { auth } from "@/auth";
import { SignJWT } from "jose";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const session = await auth();
  const user = session?.user as { id?: string; email?: string } | undefined;
  if (!user?.id || !user.email) {
    return new Response(JSON.stringify({ error: "unauthenticated" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) {
    return new Response(JSON.stringify({ error: "server-misconfigured" }), {
      status: 500,
      headers: { "content-type": "application/json" },
    });
  }

  const token = await new SignJWT({
    sub: user.id,
    email: user.email,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("15m")
    .sign(new TextEncoder().encode(secret));

  return new Response(JSON.stringify({ token }), {
    status: 200,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}
