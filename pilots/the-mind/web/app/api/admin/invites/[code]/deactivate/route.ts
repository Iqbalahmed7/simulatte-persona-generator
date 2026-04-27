/**
 * POST /api/admin/invites/[code]/deactivate — toggles invite to inactive.
 */
import { adminPost } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  _request: Request,
  ctx: { params: Promise<{ code: string }> },
) {
  const { code } = await ctx.params;
  const res = await adminPost(`/admin/invites/${encodeURIComponent(code)}/deactivate`);
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
