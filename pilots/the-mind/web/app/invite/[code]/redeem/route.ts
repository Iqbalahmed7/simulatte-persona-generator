/**
 * GET /invite/[code]/redeem — actually sets the invite_ok cookie and
 * redirects to /sign-in.
 *
 * Why this lives in a Route Handler instead of the parent page.tsx:
 * Next.js 15 forbids cookies().set() inside server components — they
 * throw because the response headers are already committed. Route
 * Handlers and Server Actions are the only places we can mutate
 * cookies. The /invite/[code] page validates the code, then redirects
 * here for the cookie write + final hop to /sign-in.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ code: string }> },
) {
  const { code } = await ctx.params;
  const jar = await cookies();
  jar.set("invite_ok", code.toUpperCase(), {
    maxAge: 60 * 60 * 24 * 60, // 60 days
    httpOnly: false,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return NextResponse.redirect(
    new URL("/sign-in?callbackUrl=/", _req.url),
    { status: 303 },
  );
}
