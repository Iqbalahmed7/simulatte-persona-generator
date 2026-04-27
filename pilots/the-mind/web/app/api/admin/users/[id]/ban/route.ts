/**
 * POST /api/admin/users/[id]/ban — server-side proxy that mints an admin
 * token and forwards to FastAPI /admin/users/{id}/ban.
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
  try { body = await request.json(); } catch { /* allow empty */ }
  const res = await adminPost(`/admin/users/${id}/ban`, body);
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
