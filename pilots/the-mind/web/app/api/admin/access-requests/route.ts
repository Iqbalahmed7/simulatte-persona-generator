/** GET /api/admin/access-requests — list. */
import { adminFetch } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const data = await adminFetch<unknown>("/admin/access-requests");
  if (data === null) {
    return new Response('{"error":"forbidden"}', { status: 403, headers: { "content-type": "application/json" } });
  }
  return Response.json(data);
}
