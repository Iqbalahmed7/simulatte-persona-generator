import { auth } from "@/auth";
import { SignJWT } from "jose";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const session = await auth();
  const user = session?.user as { id?: string; email?: string } | undefined;
  if (!user?.email) {
    return new Response("not authenticated", { status: 401 });
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
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "content-disposition":
        upstream.headers.get("content-disposition") ?? `attachment; filename="probe-${id}.json"`,
    },
  });
}
