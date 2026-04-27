/**
 * GET  /api/admin/invites — list all invite codes
 * POST /api/admin/invites — create/upsert an invite code
 *
 * Server-side proxy that mints an admin token and forwards to FastAPI.
 */
import { adminFetch, adminPost } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const data = await adminFetch<unknown>("/admin/invites");
  if (data === null) {
    return new Response('{"error":"forbidden"}', {
      status: 403,
      headers: { "content-type": "application/json" },
    });
  }
  return Response.json(data);
}

export async function POST(request: Request) {
  let body: unknown = {};
  try { body = await request.json(); } catch { /* empty */ }
  const res = await adminPost(`/admin/invites`, body);
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
