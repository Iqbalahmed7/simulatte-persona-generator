/**
 * POST /api/admin/users/[id]/set-limits
 *
 * Server-side proxy that mints an admin JWT and forwards to
 * FastAPI POST /admin/users/{id}/set-limits.
 *
 * Body: { persona_limit?: number|null, probe_limit?: number|null, chat_limit?: number|null }
 * Pass null for a field to reset it to the global default.
 */
import { adminPost } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  let body: unknown = {};
  try { body = await request.json(); } catch { /* allow empty body */ }
  const res = await adminPost(`/admin/users/${id}/set-limits`, body);
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
