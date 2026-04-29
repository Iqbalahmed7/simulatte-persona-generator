/** GET /api/admin/chats/[id]/download — stream the markdown attachment. */
import { adminGetRaw } from "@/lib/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const upstream = await adminGetRaw(`/admin/chats/${id}/download`);
  const headers = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  const disp = upstream.headers.get("content-disposition");
  if (disp) headers.set("content-disposition", disp);
  return new Response(upstream.body, { status: upstream.status, headers });
}
