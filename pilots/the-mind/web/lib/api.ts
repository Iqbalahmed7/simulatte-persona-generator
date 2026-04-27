export const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

// ── Auth helpers ──────────────────────────────────────────────────────────

/**
 * Build fetch headers that include a backend-compatible HS256 JWT.
 *
 * The Auth.js session cookie is httpOnly + JWE-encrypted, so we can't read
 * it from document.cookie or pass it to FastAPI directly. Instead, we hit
 * /api/token (Next.js Node-runtime route) which uses the httpOnly cookie
 * server-side and returns a fresh HS256 JWT signed with NEXTAUTH_SECRET —
 * which FastAPI's auth middleware already knows how to verify.
 *
 * Cached in-memory for the token's lifetime to avoid hitting /api/token on
 * every request.
 */
let _cachedToken: { value: string; expiresAt: number } | null = null;

async function _fetchToken(): Promise<string | null> {
  if (typeof window === "undefined") return null; // SSR: no auth
  const now = Date.now();
  if (_cachedToken && _cachedToken.expiresAt > now + 30_000) {
    return _cachedToken.value;
  }
  try {
    const res = await fetch("/api/token", { cache: "no-store" });
    if (!res.ok) return null;
    const { token } = await res.json();
    if (!token) return null;
    // Token is minted with 15m expiry; cache for 14m.
    _cachedToken = { value: token, expiresAt: now + 14 * 60 * 1000 };
    return token;
  } catch {
    return null;
  }
}

async function _authHeaders(): Promise<HeadersInit> {
  const token = await _fetchToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

// Re-export AllowanceError so callers can catch it
export { AllowanceError, handleApiResponse } from "@/components/AllowanceProvider";

export interface PersonaCard {
  slug: string;
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  life_stage: string;
  description: string;
  consistency_score: number;
  decision_style: string;
  trust_anchor: string;
  primary_value_orientation: string;
  portrait_url?: string;
}

export interface DecisionTrace {
  decision: string;
  confidence: number;
  gut_reaction: string;
  key_drivers: string[];
  objections: string[];
  what_would_change_mind: string;
  follow_up_action: string;
  reasoning_trace: string;
}

export interface ChatResponse {
  reply: string;
  decision_trace: DecisionTrace | null;
  persona_id: string;
  persona_name: string;
}

export async function fetchPersonas(): Promise<PersonaCard[]> {
  const res = await fetch(`${API}/personas`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load personas");
  return res.json();
}

// ── Generation types ─────────────────────────────────────────────────────

export interface ICPForm {
  brief: string;          // natural-language persona description
  domain: string;
  pdf_content?: string;   // base64-encoded PDF (optional)
}

export interface GeneratedPersonaSummary {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  life_stage: string;
  brief_snippet: string;
}

export interface GenerationEvent {
  type: "status" | "result" | "error";
  message?: string;
  persona_id?: string;
  name?: string;
}

export interface QualityAssessment {
  score: number; // 0-10
  components: Array<{ key: string; label: string; value: number; description: string }>;
  sources: Array<{ name: string; weight: string; description: string }>;
}

export interface GeneratedPersona {
  persona_id: string;
  portrait_url?: string | null;
  quality_assessment?: QualityAssessment;
  demographic_anchor: {
    name: string;
    age: number;
    gender: string;
    life_stage: string;
    location: { city: string; country: string; tier?: string };
    education: string;
    employment: { occupation: string; industry: string; seniority: string };
    household: { size: number; composition: string; monthly_income_inr?: number };
  };
  narrative: { first_person: string; third_person: string; display_name: string };
  derived_insights: {
    decision_style: string;
    trust_anchor: string;
    risk_appetite: string;
    primary_value_orientation: string;
    consistency_score: number;
    key_tensions: string[];
    coping_mechanism: { type: string; description: string };
  };
  behavioural_tendencies: {
    price_sensitivity: { band: string; description: string };
    trust_orientation: Record<string, number>;
    switching_propensity: { likelihood: string; triggers: string[] };
    objection_profile: Array<{ type: string; likelihood: string; severity: string; description: string }>;
    reasoning_prompt: string;
  };
  decision_bullets: string[];
  life_stories: Array<{ title: string; narrative: string; age_at_event?: number; emotional_weight: string }>;
  attributes: Record<string, Record<string, { value: unknown; label: string; type: string; source: string }>>;
  memory: {
    core: {
      identity_statement: string;
      key_values: string[];
      life_defining_events: string[];
      relationship_map: Record<string, string>;
      immutable_constraints: string[];
      tendency_summary: string;
    };
  };
}

export async function generatePersona(
  form: ICPForm,
  onEvent: (e: GenerationEvent) => void,
): Promise<void> {
  const res = await fetch(`${API}/generate-persona`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await _authHeaders()) },
    body: JSON.stringify(form),
  });
  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    const { AllowanceError: AE } = await import("@/components/AllowanceProvider");
    throw new AE(body.detail ?? body);
  }
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({}));
    // Moderation block: surface the user-friendly message from the API.
    if (res.status === 422 && err?.detail?.error === "moderation_blocked") {
      throw new Error(err.detail.message ?? "Content was blocked by moderation.");
    }
    throw new Error(
      typeof err.detail === "string" ? err.detail : "Generation request failed"
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
          const evt = JSON.parse(line.slice(6));
          onEvent(evt);
          // Fire-and-forget summary email after a successful generation.
          if (evt.type === "result" && evt.persona_id) {
            void notifyPersonaGenerated(evt.persona_id);
          }
        } catch { /* ignore malformed */ }
      }
    }
  }
}

/** Fire-and-forget notify hook so the backend can send a summary email. */
async function notifyPersonaGenerated(personaId: string): Promise<void> {
  try {
    await fetch(`${API}/notify/persona-generated/${personaId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(await _authHeaders()) },
    });
  } catch { /* best-effort, ignore failures */ }
}

export async function fetchGeneratedPersona(id: string): Promise<GeneratedPersona> {
  const res = await fetch(`${API}/generated/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Persona not found");
  return res.json();
}

export async function generatePortrait(personaId: string): Promise<string> {
  const res = await fetch(`${API}/generated/${personaId}/portrait`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Portrait generation failed");
  }
  const data = await res.json();
  return data.url as string;
}

export async function fetchGeneratedList(): Promise<GeneratedPersonaSummary[]> {
  try {
    const res = await fetch(`${API}/generated`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function generateExemplarPortrait(slug: string): Promise<string> {
  const res = await fetch(`${API}/personas/${slug}/portrait`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Portrait generation failed");
  }
  const data = await res.json();
  return data.url as string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchPersonaFull(slug: string): Promise<Record<string, any>> {
  const res = await fetch(`${API}/personas/${slug}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Persona not found");
  return res.json();
}

export async function chatWithGeneratedPersona(
  personaId: string,
  message: string,
  includeReasoning = true
): Promise<ChatResponse> {
  const res = await fetch(`${API}/generated/${personaId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await _authHeaders()) },
    body: JSON.stringify({ message, include_reasoning: includeReasoning }),
  });
  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    const { AllowanceError: AE } = await import("@/components/AllowanceProvider");
    throw new AE(body.detail ?? body);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Chat request failed");
  }
  return res.json();
}

// ── Probe types ───────────────────────────────────────────────────────────

export interface ClaimVerdict {
  claim: string;
  score: number;
  comment: string;
}

export interface ProbeResult {
  probe_id: string;
  persona_id: string;
  persona_name: string;
  persona_portrait_url: string | null;
  product_name: string;
  category: string;
  purchase_intent: { score: number; rationale: string };
  first_impression: { adjectives: string[]; feeling: string };
  claim_believability: ClaimVerdict[];
  differentiation: { score: number; comment: string };
  top_objection: string;
  trust_signals_needed: string[];
  price_willingness: { wtp_low: string; wtp_high: string; reaction: string };
  word_of_mouth: { likelihood: number; what_theyd_say: string };
  created_at: string;
}

export interface ProbeSummary {
  probe_id: string;
  product_name: string;
  purchase_intent: number;
  created_at: string;
}

export async function runProbe(
  personaId: string,
  brief: {
    product_name: string;
    category: string;
    description: string;
    claims: string[];
    price: string;
    image_url?: string;
    pdf_content?: string;     // base64, no data: prefix
    pdf_filename?: string;
  }
): Promise<ProbeResult> {
  const res = await fetch(`${API}/generated/${personaId}/probe`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await _authHeaders()) },
    body: JSON.stringify(brief),
  });
  if (res.status === 402) {
    const body = await res.json().catch(() => ({}));
    const { AllowanceError: AE } = await import("@/components/AllowanceProvider");
    throw new AE(body.detail ?? body);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    // Surface moderation-friendly message
    const detail = (err as { detail?: unknown }).detail;
    if (
      res.status === 422 &&
      detail && typeof detail === "object" &&
      (detail as { error?: string }).error === "moderation_blocked"
    ) {
      throw new Error((detail as { message?: string }).message ?? "Content was blocked.");
    }
    throw new Error(
      typeof detail === "string" ? detail : "Probe failed"
    );
  }
  return res.json();
}

export async function fetchProbe(probeId: string): Promise<ProbeResult> {
  const res = await fetch(`${API}/probes/${probeId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Probe not found");
  return res.json();
}

export async function fetchProbesForPersona(personaId: string): Promise<ProbeSummary[]> {
  try {
    const res = await fetch(`${API}/generated/${personaId}/probes`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function chatWithPersona(
  slug: string,
  message: string,
  includeReasoning = true
): Promise<ChatResponse> {
  const res = await fetch(`${API}/personas/${slug}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, include_reasoning: includeReasoning }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Chat request failed");
  }
  return res.json();
}
