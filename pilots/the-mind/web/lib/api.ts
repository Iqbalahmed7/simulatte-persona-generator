const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

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
