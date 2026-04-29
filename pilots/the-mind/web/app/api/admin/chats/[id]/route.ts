/** GET /api/admin/chats/[id] — full chat session payload (header + messages). */
import { adminFetch } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const data = await adminFetch<unknown>(`/admin/chats/${id}`);
  if (data === null) {
    return new Response('{"error":"forbidden_or_missing"}', { status: 404 });
  }
  return Response.json(data);
}
