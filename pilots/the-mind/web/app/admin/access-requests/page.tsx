/**
 * /admin/access-requests — pending users who hit "Request access" on the
 * waitlist screen. Admin can approve (flips pending→active and sends them
 * a welcome email) or dismiss.
 */
import { adminFetch } from "@/lib/admin";
import AccessRequestsClient from "./AccessRequestsClient";

export const dynamic = "force-dynamic";

interface AccessRequestRow {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string | null;
  user_image: string | null;
  user_access_status: string;
  reason: string | null;
  status: string;
  created_at: string | null;
  resolved_at: string | null;
  resolved_by_email: string | null;
}

export default async function AdminAccessRequestsPage() {
  const rows = (await adminFetch<AccessRequestRow[]>("/admin/access-requests")) ?? [];
  return (
    <div>
      <h1 className="font-condensed font-black text-3xl uppercase tracking-wider mb-2">
        Access Requests
      </h1>
      <p className="text-parchment/72 mb-8 max-w-2xl">
        Organic sign-ups asking to be let in. Approve to activate them and
        send a welcome email; dismiss to leave them on the waitlist.
      </p>
      <AccessRequestsClient initialRows={rows} />
    </div>
  );
}
