const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Question {
  slot_id: string;
  question: string;
  chips: string[];
  allow_freetext: boolean;
}

export interface ScoreOut {
  composite: number;
  dimensions: Record<string, number>;
  suggestions: string[];
}

export interface GenerationResult {
  prompt: string;
  score: ScoreOut;
  prompt_version_id: string;
}

export interface TurnResponse {
  session_id: string;
  status: "needs_question" | "done";
  question: Question | null;
  result: GenerationResult | null;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export const startGeneration = (input: string) =>
  post<TurnResponse>("/generate/start", { input });

export const submitAnswer = (session_id: string, slot_id: string, answer: string) =>
  post<TurnResponse>("/generate/answer", { session_id, slot_id, answer });

export const runPrompt = (prompt_version_id: string) =>
  post<{ output: string }>("/generate/run", { prompt_version_id });

export const ratePrompt = (prompt_version_id: string, rating: 1 | -1, feedback?: string) =>
  post<{ ok: boolean }>("/generate/rate", { prompt_version_id, rating, feedback });
