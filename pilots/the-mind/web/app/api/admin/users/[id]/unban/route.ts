/**
 * POST /api/admin/users/[id]/unban — proxy to FastAPI /admin/users/{id}/unban.
 */
import { adminPost } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  _request: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  const res = await adminPost(`/admin/users/${id}/unban`);
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
