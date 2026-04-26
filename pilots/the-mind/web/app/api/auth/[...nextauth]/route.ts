/**
 * app/api/auth/[...nextauth]/route.ts — Auth.js v5 route handler.
 *
 * Mounts all Auth.js endpoints under /api/auth/:
 *   GET  /api/auth/signin
 *   POST /api/auth/signin/google
 *   POST /api/auth/signin/resend
 *   GET  /api/auth/callback/google
 *   GET  /api/auth/callback/resend
 *   GET  /api/auth/signout
 *   GET  /api/auth/session
 *   GET  /api/auth/csrf
 */
export { handlers as GET, handlers as POST } from "@/auth";
