/**
 * lib/admin.ts — server-side helpers for the admin dashboard.
 *
 * Used by /admin/* server components. All data fetches go through here so
 * we can centralize the JWT minting + FastAPI URL.
 */
import { auth } from "@/auth";
import { SignJWT } from "jose";

export const ADMIN_API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"
).trim();

const ADMIN_EMAILS: Set<string> = new Set(
  (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)
);

export async function getAdminUser() {
  const session = await auth();
  const user = session?.user as { id?: string; email?: string; name?: string } | undefined;
  if (!user?.email) return null;
  if (!ADMIN_EMAILS.has(user.email.toLowerCase())) return null;
  return user;
}

async function _mintToken(user: { id?: string; email?: string }): Promise<string> {
  const secret = process.env.NEXTAUTH_SECRET ?? "";
  return await new SignJWT({ sub: user.id, email: user.email })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(new TextEncoder().encode(secret));
}

export async function adminFetch<T = unknown>(path: string): Promise<T | null> {
  const user = await getAdminUser();
  if (!user) return null;
  const token = await _mintToken(user);
  const res = await fetch(`${ADMIN_API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as T;
}

/** Minted-token POST proxy. Returns Response so the caller can decide on
 *  status / body shape. Used by /api/admin/* route handlers. */
export async function adminPost(path: string, body?: unknown): Promise<Response> {
  const user = await getAdminUser();
  if (!user) return new Response('{"error":"forbidden"}', { status: 403 });
  const token = await _mintToken(user);
  return await fetch(`${ADMIN_API_BASE}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
}
