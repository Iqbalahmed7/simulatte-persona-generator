/**
 * middleware.ts — Next.js Edge middleware.
 *
 * Two layers of access control:
 *
 *   1. Invite gate (private launch): every public route is gated by either
 *      an `invite_ok` cookie OR a logged-in session. Unauthenticated, un-
 *      invited visitors are redirected to /welcome. Whitelisted paths
 *      (/welcome, /invite/*, /sign-in, /api/auth/*, public assets) are
 *      always accessible.
 *
 *   2. Session gate (existing): authed-only routes (/generate, /admin,
 *      /persona/[id]/probe) require an Auth.js session cookie. Without one
 *      the user is sent to /sign-in.
 *
 * We don't verify JWTs at the Edge — Auth.js v5 + Edge crypto is flaky on
 * custom domains. Server components / route handlers do the real auth.
 */
import { NextRequest, NextResponse } from "next/server";

const PROTECTED_PREFIXES = ["/generate", "/admin"];

function isPathProtected(pathname: string): boolean {
  if (PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))) return true;
  // /persona/[id]/probe — probe form (consumes allowance, must be authed).
  if (/^\/persona\/[^/]+\/probe(?:\/.*)?$/.test(pathname)) return true;
  return false;
}

// Paths that are always reachable without invite or session.
const PUBLIC_WHITELIST_PREFIXES = [
  "/welcome",
  "/invite/",
  "/sign-in",
  "/api/auth/",
  "/api/token",
  "/api/invite/",
  "/_next/",
  "/probe/",            // public probe-share leaf URLs
  "/community",
];
const PUBLIC_WHITELIST_EXACT = new Set([
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
]);

function isPublicWhitelisted(pathname: string): boolean {
  if (PUBLIC_WHITELIST_EXACT.has(pathname)) return true;
  if (PUBLIC_WHITELIST_PREFIXES.some((p) => pathname.startsWith(p))) return true;
  // any static asset
  if (/\.(svg|png|jpg|jpeg|gif|webp|ico|css|js|map|txt|woff2?)$/i.test(pathname)) {
    return true;
  }
  return false;
}

const SESSION_COOKIE_NAMES = [
  "__Secure-authjs.session-token",
  "authjs.session-token",
];

function hasSession(request: NextRequest): boolean {
  return SESSION_COOKIE_NAMES.some((n) => !!request.cookies.get(n)?.value);
}

function hasInvite(request: NextRequest): boolean {
  return !!request.cookies.get("invite_ok")?.value;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always-allowed paths
  if (isPublicWhitelisted(pathname)) return NextResponse.next();

  // Invite gate (private-launch). Disabled if NEXT_PUBLIC_INVITE_GATE=off.
  const inviteGateEnabled =
    (process.env.NEXT_PUBLIC_INVITE_GATE ?? "on").toLowerCase() !== "off";

  if (inviteGateEnabled && !hasInvite(request) && !hasSession(request)) {
    const welcomeUrl = new URL("/welcome", request.url);
    if (pathname !== "/") {
      welcomeUrl.searchParams.set("from", pathname);
    }
    return NextResponse.redirect(welcomeUrl);
  }

  // Session gate (auth-required pages)
  if (isPathProtected(pathname)) {
    if (hasSession(request)) return NextResponse.next();
    const signInUrl = new URL("/sign-in", request.url);
    signInUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(signInUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|.*\\.svg).*)",
  ],
};
