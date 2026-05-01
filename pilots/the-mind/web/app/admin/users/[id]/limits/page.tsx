/**
 * app/admin/users/[id]/limits/page.tsx
 *
 * Server component shell that loads current-week allowance state,
 * then renders the interactive OperatorLimitsForm client component.
 */

import Link from "next/link";
import { adminFetch, getAdminUser } from "@/lib/admin";
import { redirect } from "next/navigation";
import OperatorLimitsForm from "./OperatorLimitsForm";

interface AllowanceState {
  user_id:       string;
  week_starting: string;
  twins_built:   number;
  twin_refreshes: number;
  probe_messages: number;
  frame_scores:  number;
  limits: {
    twin_build:    number;
    twin_refresh:  number;
    probe_message: number;
    frame_score:   number;
  };
}

interface UserSummary {
  user: { id: string; email: string; name: string | null };
}

export default async function AdminUserLimitsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const adminUser = await getAdminUser();
  if (!adminUser) redirect("/");

  const [userInfo, allowance] = await Promise.all([
    adminFetch<UserSummary>(`/admin/users/${id}`),
    adminFetch<AllowanceState>(`/operator/admin/users/${id}/allowance`),
  ]);

  const email = userInfo?.user?.email ?? id;
  const name  = userInfo?.user?.name  ?? null;

  return (
    <div className="space-y-4 max-w-lg">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-mono text-static">
        <Link href="/admin/users" className="hover:text-parchment transition-colors">Users</Link>
        <span>/</span>
        <Link href={`/admin/users/${id}`} className="hover:text-parchment transition-colors truncate max-w-[160px]">
          {email}
        </Link>
        <span>/</span>
        <span className="text-parchment">Operator limits</span>
      </div>

      <div>
        <p className="text-static text-[10px] font-mono uppercase tracking-wider">Operator</p>
        <h1 className="text-parchment text-lg font-semibold">
          {name ?? email}
        </h1>
        <p className="text-static text-xs font-mono mt-0.5">
          Week of {allowance?.week_starting ?? "—"}
        </p>
      </div>

      <OperatorLimitsForm userId={id} initial={allowance} />
    </div>
  );
}
