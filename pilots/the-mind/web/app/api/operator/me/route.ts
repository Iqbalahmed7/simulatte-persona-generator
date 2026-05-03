/**
 * GET /api/operator/me — return the current user's ID and email.
 *
 * Reads the Auth.js session server-side (no CORS issues) and returns the
 * same user_id that the FastAPI backend uses. Use this to find your
 * target_user_id for Trinity pipeline builds.
 */
import { auth } from "@/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const session = await auth();
  const user = session?.user as { id?: string; email?: string } | undefined;

  if (!user?.email) {
    return new Response(JSON.stringify({ error: "unauthenticated" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  return new Response(
    JSON.stringify({ user_id: user.id ?? null, email: user.email }),
    { status: 200, headers: { "content-type": "application/json", "cache-control": "no-store" } }
  );
}
