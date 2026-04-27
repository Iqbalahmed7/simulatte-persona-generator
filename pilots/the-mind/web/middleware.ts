/**
 * middleware.ts — Next.js Edge middleware protecting authenticated routes.
 *
 * Strategy: simple cookie-presence check. We don't verify the JWT here
 * because Auth.js v5 + Edge runtime + custom domain has been flaky with
 * crypto. The route handlers and server components do the real session
 * verification (via auth() from ./auth on the Node runtime), so a stolen
 * cookie can't actually do anything — middleware just keeps unauthenticated
 * users out of the protected page shells.
 *
 * Gated routes (redirect to /sign-in if no session cookie):
 *   /generate       — persona generation form
 *   /probe/*        — probe form (the public /probe/[probeId] share view
 *                     is a leaf URL not matched by /probe/ + path; new
 *                     probes are created from the persona page)
 *
 * Public read-only routes (no middleware gate):
 *   /persona/[id]   — Community Wall makes all generated personas public.
 *                     Chat / "Run a probe" buttons trigger sign-in only on
 *                     interaction; the page itself is browseable by anyone.
 */
import { NextRequest, NextResponse } from "next/server";

const PROTECTED_PREFIXES = ["/generate"];

/** Returns true if the path needs an auth gate. */
function isPathProtected(pathname: string): boolean {
  if (PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))) return true;
  // /persona/[id]/probe — probe form (consumes allowance, must be authed).
  // The bare /persona/[id] view is public for community-wall browsing.
  if (/^\/persona\/[^/]+\/probe(?:\/.*)?$/.test(pathname)) return true;
  return false;
}

// Auth.js v5 cookie names. On HTTPS the prefix is __Secure-; on HTTP it isn't.
const SESSION_COOKIE_NAMES = [
  "__Secure-authjs.session-token",
  "authjs.session-token",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!isPathProtected(pathname)) return NextResponse.next();

  const hasSession = SESSION_COOKIE_NAMES.some(
    (name) => !!request.cookies.get(name)?.value
  );
  if (hasSession) return NextResponse.next();

  const signInUrl = new URL("/sign-in", request.url);
  signInUrl.searchParams.set("callbackUrl", pathname);
  return NextResponse.redirect(signInUrl);
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.svg).*)",
  ],
};
