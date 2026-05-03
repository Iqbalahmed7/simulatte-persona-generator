/**
 * POST /api/operator/admin/reattribute
 *
 * Server-side proxy that mints an admin JWT from the Auth.js session and
 * forwards to the FastAPI migration endpoint. Avoids browser CORS issues
 * when calling the Railway backend from mind.simulatte.io.
 *
 * Re-attributes all twins owned by `service-operator` to the caller's user_id
 * (or to a target_user_id passed in the body, admin only). Idempotent.
 */
import { auth } from "@/auth";
import { SignJWT } from "jose";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

export async function POST(req: Request) {
  const session = await auth();
  const user = session?.user as { id?: string; email?: string } | undefined;
  if (!user?.email) {
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

  // Accept body override but default to caller's user_id
  let target_user_id = user.id;
  try {
    const body = await req.json().catch(() => ({}));
    if (body?.target_user_id && typeof body.target_user_id === "string") {
      target_user_id = body.target_user_id;
    }
  } catch {
    // empty body is fine
  }

  const token = await new SignJWT({ sub: user.id, email: user.email })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(new TextEncoder().encode(secret));

  const upstream = await fetch(
    `${API}/operator/admin/migrate/reattribute-service-twins`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ target_user_id }),
      cache: "no-store",
    },
  );

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}
