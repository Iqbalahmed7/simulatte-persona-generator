/**
 * app/operator/layout.tsx — Admin-only gate for all Operator (The Twin) routes.
 *
 * Hard 404 for any non-admin user. All Operator pages are children of this
 * layout so the check is enforced once rather than in every page.
 *
 * Wraps children in OperatorAllowanceProvider so any page can surface
 * the 402 modal without wiring it per-page.
 */
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import OperatorAllowanceProvider from "@/components/OperatorAllowanceProvider";
import { getAdminUser } from "@/lib/admin";

export default async function OperatorLayout({ children }: { children: ReactNode }) {
  // Operator is admin-only until it graduates to a full product.
  // No env flag needed — the isAdmin check is the gate.
  const admin = await getAdminUser();
  if (!admin) notFound();

  return <OperatorAllowanceProvider>{children}</OperatorAllowanceProvider>;
}
