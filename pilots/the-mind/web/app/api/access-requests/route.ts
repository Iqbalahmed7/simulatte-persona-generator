/**
 * POST /api/access-requests — same-origin proxy to FastAPI's
 * /access-requests (waitlist user submits "tell us why").
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
  const body = await request.text();
  const upstream = await fetch(`${API}/access-requests`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "content-type": "application/json" },
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
