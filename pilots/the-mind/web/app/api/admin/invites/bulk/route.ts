/**
 * POST /api/admin/invites/bulk — mint many invite codes in one shot.
 *
 * Same-origin proxy to FastAPI. The FastAPI route loops over the
 * items, mints unique codes, optionally fires emails, and returns
 * a per-row results array.
 */
import { adminPost } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  let body: unknown = {};
  try { body = await request.json(); } catch { /* empty */ }
  const res = await adminPost("/admin/invites/bulk", body);
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
