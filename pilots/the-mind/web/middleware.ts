/**
 * middleware.ts — Next.js Edge middleware protecting authenticated routes.
 *
 * IMPORTANT: imports ONLY from ./auth.config (Edge-safe, no pg/Node APIs).
 * Never import from ./auth here — pg (net/tls) will break the Edge build.
 *
 * Gated routes (redirect to /sign-in if no session):
 *   /generate       — persona generation form
 *   /persona/*      — individual persona pages
 *   /probe/*        — probe form and results
 *
 * Public routes (no auth needed):
 *   /               — landing + exemplar personas
 *   /sign-in        — sign-in page
 *   /api/auth/*     — Auth.js handlers (excluded by matcher)
 */
import NextAuth from "next-auth";
import { authConfig } from "./auth.config";

export const { auth: middleware } = NextAuth(authConfig);

export const config = {
  matcher: [
    // Skip Next.js internals, static files, and auth API routes.
    // Run on all other paths so the authorized() callback can gate them.
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.svg).*)",
  ],
};
