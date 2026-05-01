/**
 * app/api/admin/operator/users/[user_id]/allowance/route.ts
 *
 * GET  — proxy to GET  /operator/admin/users/{user_id}/allowance
 * PATCH — proxy to PATCH /operator/admin/users/{user_id}/allowance
 *
 * Used by the client-side OperatorLimitsForm on /admin/users/[id]/limits.
 */

import { adminFetch, ADMIN_API_BASE, getAdminUser } from "@/lib/admin";
import { SignJWT } from "jose";
import { NextRequest, NextResponse } from "next/server";

async function mintToken(user: { id?: string; email?: string }) {
  const secret = process.env.NEXTAUTH_SECRET ?? "";
  return await new SignJWT({ sub: user.id, email: user.email })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(new TextEncoder().encode(secret));
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ user_id: string }> }
) {
  const { user_id } = await params;
  const data = await adminFetch(`/operator/admin/users/${user_id}/allowance`);
  if (!data) return NextResponse.json({ error: "forbidden or not found" }, { status: 403 });
  return NextResponse.json(data);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ user_id: string }> }
) {
  const { user_id } = await params;
  const user = await getAdminUser();
  if (!user) return NextResponse.json({ error: "forbidden" }, { status: 403 });

  const token = await mintToken(user);
  const body = await req.json();

  const res = await fetch(`${ADMIN_API_BASE}/operator/admin/users/${user_id}/allowance`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
