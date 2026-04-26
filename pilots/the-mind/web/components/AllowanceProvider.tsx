"use client";

/**
 * AllowanceProvider.tsx — Context provider + global modal for 402 handling.
 *
 * Wraps the app with:
 *   1. AllowanceContext — exposes `triggerAllowanceExceeded(payload)` so any
 *      component can surface the hard-wall modal.
 *   2. Automatically patches lib/api.ts fetch calls via the context callback.
 *
 * Usage:
 *   // In a page or component:
 *   const { triggerAllowanceExceeded } = useAllowance();
 *
 *   // Or use the standalone helper:
 *   import { handleApiResponse } from "@/components/AllowanceProvider";
 *   const data = await handleApiResponse(res); // throws AllowanceError or returns json
 */
import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import AllowanceModal, {
  type AllowanceExceededPayload,
} from "./AllowanceModal";

// ── Context ───────────────────────────────────────────────────────────────

interface AllowanceContextValue {
  triggerAllowanceExceeded: (payload: AllowanceExceededPayload) => void;
}

const AllowanceContext = createContext<AllowanceContextValue>({
  triggerAllowanceExceeded: () => undefined,
});

export function useAllowance() {
  return useContext(AllowanceContext);
}

// ── Provider ──────────────────────────────────────────────────────────────

export default function AllowanceProvider({ children }: { children: ReactNode }) {
  const [payload, setPayload] = useState<AllowanceExceededPayload | null>(null);

  const triggerAllowanceExceeded = useCallback(
    (p: AllowanceExceededPayload) => setPayload(p),
    []
  );

  return (
    <AllowanceContext.Provider value={{ triggerAllowanceExceeded }}>
      {children}
      {payload && (
        <AllowanceModal payload={payload} onClose={() => setPayload(null)} />
      )}
    </AllowanceContext.Provider>
  );
}

// ── Standalone helper — use in API functions ──────────────────────────────

export class AllowanceError extends Error {
  constructor(public payload: AllowanceExceededPayload) {
    super("allowance_exceeded");
    this.name = "AllowanceError";
  }
}

/**
 * Wraps a fetch Response: throws AllowanceError on 402, rethrows other errors,
 * returns parsed JSON on success.
 */
export async function handleApiResponse<T = unknown>(res: Response): Promise<T> {
  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail ?? body;
    if (detail?.error === "allowance_exceeded") {
      throw new AllowanceError(detail as AllowanceExceededPayload);
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ?? `HTTP ${res.status}`
    );
  }
  return res.json() as Promise<T>;
}
