/**
 * lib/operator-api.ts — API helpers for The Operator (Prospect Twin System).
 *
 * Mirrors the shape of lib/api.ts. All requests reuse _authHeaders() from
 * lib/api.ts. Feature-gated: callers should check NEXT_PUBLIC_OPERATOR_ENABLED
 * before rendering any Operator UI.
 */

import { API } from "./api";

// Re-export auth helper so Operator callers don't import from api.ts directly
async function _authHeaders(): Promise<HeadersInit> {
  if (typeof window === "undefined") return {};
  try {
    const res = await fetch("/api/token", { cache: "no-store" });
    if (!res.ok) return {};
    const { token } = await res.json();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  } catch {
    return {};
  }
}

// ── Types ─────────────────────────────────────────────────────────────────

export type ConfidenceTier = "high" | "medium" | "low";

export interface TwinCard {
  twin_id: string;
  full_name: string;
  title: string | null;
  company: string | null;
  confidence: ConfidenceTier;
  last_refreshed_at: string | null;
  is_stale: boolean;
  probe_count: number;
  last_frame_score: number | null;
  portrait_url: string | null;
}

export interface TwinObjPair {
  objection: string;
  preempt: string;
  response: string;
}

export interface TwinDetail {
  twin_id: string;
  full_name: string;
  title: string | null;
  company: string | null;
  confidence: ConfidenceTier;
  last_refreshed_at: string | null;
  is_stale: boolean;
  recon_source_count: number;
  probe_count: number;
  last_frame_score: number | null;
  portrait_url: string | null;

  // Profile sections
  identity_snapshot: string;
  decision_architecture: {
    first_filter: string;
    trust_signal: string;
    rejection_trigger: string;
    engagement_threshold: string;
  };
  trigger_map: {
    leans_in: string[];
    disengages: string[];
  };
  objection_anticipator: {
    first_contact: TwinObjPair[];
    first_call: TwinObjPair[];
  };
  message_frame_recommendations: {
    lead_with: string;
    avoid: string;
    tone: string;
    format: string;
    timing: string;
  };
  call_prep: {
    have_ready: string[];
    do_not_say: string[];
  };
  gaps: string[];
}

export interface FrameAnnotation {
  segment: string;
  start: number;
  end: number;
  score: number;
  reads_as: string;
  risk: string | null;
}

export interface FrameScoreResponse {
  frame_id: string;
  twin_id: string;
  overall_score: number;
  reply_probability: "high" | "medium" | "low";
  annotations: FrameAnnotation[];
  strongest_point: { segment: string; reason: string } | null;
  weakest_point: { segment: string; issue: string } | null;
  single_improvement: string;
  scored_at: string;
}

export interface OperatorAllowanceState {
  twins: { used: number; limit: number };
  probe_messages: { used: number; limit: number };
  resets_at: string;
}

export interface OperatorMeResponse {
  allowance: OperatorAllowanceState;
}

export interface ProbeSession {
  session_id: string;
  twin_id: string;
  created_at: string;
  last_active_at: string;
  message_count: number;
  ended: boolean;
}

export interface ProbeMessage {
  message_id: string;
  session_id: string;
  role: "user" | "twin";
  content: string;
  operator_note: string | null;
  created_at: string;
}

// ── Build SSE event types ─────────────────────────────────────────────────

export interface BuildSSEEvent {
  stage: "recon" | "synthesis" | "ready" | "error";
  message?: string;
  twin_id?: string;
  error?: string;
  error_code?: string;
}

// ── Probe SSE event types ─────────────────────────────────────────────────

export interface ProbeSSEEvent {
  type: "token" | "operator_note" | "done" | "error";
  content?: string;
  note?: string;
  error?: string;
  error_code?: string;
}

// ── Error handling ────────────────────────────────────────────────────────

export class OperatorAllowanceError extends Error {
  constructor(
    public payload: {
      error: string;
      action: string;
      used: number;
      limit: number;
      resets_at: string;
      upgrade_url?: string;
    }
  ) {
    super("operator_allowance_exceeded");
    this.name = "OperatorAllowanceError";
  }
}

// Human-readable messages for known error codes
export const OPERATOR_ERROR_MESSAGES: Record<string, string> = {
  eu_subject_blocked: "EU-based subjects are unavailable in Phase 1.",
  recon_insufficient:
    "Not enough public information found. Try adding a company or title.",
  twin_not_found: "This Twin no longer exists.",
  session_ended: "Session ended (idle 30 min). Start a new session.",
  moderation_blocked: "This subject or content was blocked by moderation.",
};

async function _handleOperatorResponse<T>(res: Response): Promise<T> {
  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    throw new OperatorAllowanceError(body.detail ?? body);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : (detail as { message?: string })?.message ?? `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

// ── Allowance ─────────────────────────────────────────────────────────────

export async function getOperatorAllowance(): Promise<OperatorAllowanceState | null> {
  try {
    const headers = await _authHeaders();
    const res = await fetch(`${API}/operator/me`, {
      headers,
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data: OperatorMeResponse = await res.json();
    return data.allowance;
  } catch {
    return null;
  }
}

// ── Twins CRUD ────────────────────────────────────────────────────────────

export async function listTwins(): Promise<TwinCard[]> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins`, {
    headers,
    cache: "no-store",
  });
  return _handleOperatorResponse<TwinCard[]>(res);
}

export async function getTwin(twinId: string): Promise<TwinDetail> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins/${twinId}`, {
    headers,
    cache: "no-store",
  });
  return _handleOperatorResponse<TwinDetail>(res);
}

export async function deleteTwin(twinId: string): Promise<void> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins/${twinId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Delete failed");
  }
}

// ── Build (SSE stream) ────────────────────────────────────────────────────

export async function streamBuild(
  form: { full_name: string; company?: string; title?: string },
  onEvent: (e: BuildSSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(form),
    signal,
  });

  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    throw new OperatorAllowanceError(body.detail ?? body);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    throw new Error(
      typeof detail === "string" ? detail : `Build request failed (${res.status})`
    );
  }

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const evt = JSON.parse(line.slice(6)) as BuildSSEEvent;
          onEvent(evt);
        } catch { /* ignore malformed */ }
      }
    }
  }
}

// ── Refresh (SSE stream) ──────────────────────────────────────────────────

export async function streamRefresh(
  twinId: string,
  onEvent: (e: BuildSSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins/${twinId}/refresh`, {
    method: "POST",
    headers,
    signal,
  });

  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    throw new OperatorAllowanceError(body.detail ?? body);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Refresh failed");
  }

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          onEvent(JSON.parse(line.slice(6)) as BuildSSEEvent);
        } catch { /* ignore */ }
      }
    }
  }
}

// ── Enrich ────────────────────────────────────────────────────────────────

export async function enrichTwin(
  twinId: string,
  text: string
): Promise<TwinDetail> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins/${twinId}/enrich`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return _handleOperatorResponse<TwinDetail>(res);
}

// ── Probe sessions ────────────────────────────────────────────────────────

export async function startProbeSession(twinId: string): Promise<ProbeSession> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins/${twinId}/probe`, {
    method: "POST",
    headers,
  });
  return _handleOperatorResponse<ProbeSession>(res);
}

export async function endProbeSession(
  twinId: string,
  sessionId: string
): Promise<void> {
  const headers = await _authHeaders();
  const res = await fetch(
    `${API}/operator/twins/${twinId}/probe/${sessionId}/end`,
    { method: "POST", headers }
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "End session failed");
  }
}

export async function streamProbeMessage(
  twinId: string,
  sessionId: string,
  message: string,
  onEvent: (e: ProbeSSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const headers = await _authHeaders();
  const res = await fetch(
    `${API}/operator/twins/${twinId}/probe/${sessionId}/message`,
    {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal,
    }
  );

  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    throw new OperatorAllowanceError(body.detail ?? body);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Message failed");
  }

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          onEvent(JSON.parse(line.slice(6)) as ProbeSSEEvent);
        } catch { /* ignore */ }
      }
    }
  }
}

// ── Frame score ───────────────────────────────────────────────────────────

// ── Portrait ──────────────────────────────────────────────────────────────

export async function generateTwinPortrait(
  twinId: string,
  force = false
): Promise<string> {
  const headers = await _authHeaders();
  const url = `${API}/operator/twins/${twinId}/portrait${force ? "?force=true" : ""}`;
  const res = await fetch(url, { method: "POST", headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ?? `Portrait generation failed (${res.status})`
    );
  }
  const data = await res.json();
  return (data as { url: string }).url;
}

// ── Frame score ───────────────────────────────────────────────────────────

export async function frameScore(
  twinId: string,
  draft: string
): Promise<FrameScoreResponse> {
  const headers = await _authHeaders();
  const res = await fetch(`${API}/operator/twins/${twinId}/frame`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ draft }),
  });
  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    throw new OperatorAllowanceError(body.detail ?? body);
  }
  return _handleOperatorResponse<FrameScoreResponse>(res);
}
