import type { TurnResponse } from "@/lib/generate-api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface VersionSummary {
  id: string;
  content_preview: string;
  score: number | null;
  outcome_label: string | null;
  created_at: string;
}

export interface PromptGroupOut {
  group_id: string;
  root_prompt_id: string;
  title: string | null;
  domain: string | null;
  version_count: number;
  latest_version: VersionSummary;
  created_at: string;
}

export interface VersionDetailOut {
  id: string;
  content: string;
  score_json: Record<string, unknown> | null;
  outcome_label: string | null;
  created_at: string;
}

export interface PromptDetailOut {
  id: string;
  group_id: string;
  title: string | null;
  domain: string | null;
  skills_applied: string[] | null;
  score: number | null;
  branched_from_version_id: string | null;
  created_at: string;
  versions: VersionDetailOut[];
}

export interface PromptGroupDetailOut {
  group_id: string;
  prompts: PromptDetailOut[];
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("pf_token");
}

async function libFetch<T>(path: string, method: string, body?: unknown): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export const listLibrary = (domain?: string) =>
  libFetch<PromptGroupOut[]>(`/library${domain ? `?domain=${encodeURIComponent(domain)}` : ""}`, "GET");

export const getPromptGroup = (promptId: string) =>
  libFetch<PromptGroupDetailOut>(`/library/${promptId}`, "GET");

export const updatePromptTitle = (promptId: string, title: string) =>
  libFetch<{ ok: boolean }>(`/library/${promptId}`, "PATCH", { title });

export const labelVersion = (promptId: string, versionId: string, outcome_label: string | null) =>
  libFetch<{ ok: boolean }>(`/library/${promptId}/versions/${versionId}`, "PATCH", { outcome_label });

export const deletePrompt = (promptId: string) =>
  libFetch<{ ok: boolean }>(`/library/${promptId}`, "DELETE");

export const branchVersion = (promptVersionId: string) =>
  libFetch<TurnResponse>("/generate/branch", "POST", { prompt_version_id: promptVersionId });
