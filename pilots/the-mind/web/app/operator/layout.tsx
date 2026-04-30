/**
 * app/operator/layout.tsx — Feature flag gate for all Operator routes.
 *
 * Hard 404 when NEXT_PUBLIC_OPERATOR_ENABLED !== "true".
 * All Operator pages are children of this layout so the flag is enforced
 * once rather than in every page.
 *
 * Wraps children in OperatorAllowanceProvider so any page can surface
 * the 402 modal without wiring it per-page.
 */
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import OperatorAllowanceProvider from "@/components/OperatorAllowanceProvider";

export default function OperatorLayout({ children }: { children: ReactNode }) {
  if (process.env.NEXT_PUBLIC_OPERATOR_ENABLED !== "true") {
    notFound();
  }

  return <OperatorAllowanceProvider>{children}</OperatorAllowanceProvider>;
}
