/**
 * middleware.ts — Next.js middleware protecting authenticated routes.
 *
 * Gated routes (redirect to /sign-in if no session):
 *   /generate       — persona generation form
 *   /persona/*      — individual persona pages
 *   /probe/*        — probe form and results
 *
 * Public routes (no auth needed):
 *   /               — landing + exemplar personas
 *   /[slug]/*       — exemplar chat pages
 *   /sign-in        — sign-in page
 *   /api/auth/*     — Auth.js handlers
 */
export { auth as middleware } from "@/auth";

export const config = {
  matcher: [
    "/generate",
    "/generate/:path*",
    "/persona/:path*",
    "/probe/:path*",
  ],
};
