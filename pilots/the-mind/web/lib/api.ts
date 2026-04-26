export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

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

export interface GeneratedPersona {
  persona_id: string;
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Generation request failed");
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
          onEvent(JSON.parse(line.slice(6)));
        } catch { /* ignore malformed */ }
      }
    }
  }
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
