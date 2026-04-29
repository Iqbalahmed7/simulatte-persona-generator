/** GET /api/admin/users/[id]/chats — list chat sessions for a user. */
import { adminFetch } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const data = await adminFetch<unknown>(`/admin/users/${id}/chats`);
  if (data === null) {
    return new Response('{"error":"forbidden"}', { status: 403 });
  }
  return Response.json(data);
}
