/**
 * /admin/invites — create + list invite codes.
 *
 * Server-rendered initial list, client form for create & deactivate.
 */
import { adminFetch } from "@/lib/admin";
import InvitesClient from "./InvitesClient";

export const dynamic = "force-dynamic";

interface InviteRow {
  code: string;
  label: string | null;
  max_uses: number | null;
  used_count: number;
  actual_redemptions: number;
  active: boolean;
  created_at: string | null;
  created_by_email: string | null;
}

export default async function AdminInvitesPage() {
  const codes = (await adminFetch<InviteRow[]>("/admin/invites")) ?? [];
  return (
    <div>
      <h1 className="font-condensed font-black text-3xl uppercase tracking-wider mb-2">
        Invite Codes
      </h1>
      <p className="text-parchment/72 mb-8 max-w-2xl">
        One code can be shared with many people. Track redemption velocity per
        code to see which channels are spreading the product.
      </p>
      <InvitesClient initialCodes={codes} />
    </div>
  );
}
