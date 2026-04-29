import { auth } from "@/auth";
import { SignJWT } from "jose";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

/**
 * GET /api/probes/[id]/full — same-origin proxy to the FastAPI download
 * endpoint, but strips the Content-Disposition header so callers can
 * render the JSON inline (e.g. admin "expand verdicts" toggle).
 */
export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
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

  const upstream = await fetch(`${API}/probes/${encodeURIComponent(id)}/download`, {
    headers: { Authorization: `Bearer ${token}` },
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
