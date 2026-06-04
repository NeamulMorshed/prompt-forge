const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Profile {
  id: string;
  name: string;
  core_context: Record<string, string>;
  domain_overrides: Record<string, Record<string, string>>;
  updated_at: string;
}

export interface ProfileUpsert {
  core_context: Record<string, string>;
  domain_overrides: Record<string, Record<string, string>>;
}

export interface ExtractOut {
  core_context: Record<string, string>;
  domain_overrides: Record<string, Record<string, string>>;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("pf_token");
}

async function profileFetch<T>(
  path: string,
  method: string,
  body?: unknown,
): Promise<T> {
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

export const getProfile = () =>
  profileFetch<Profile | null>("/profile", "GET");

export const upsertProfile = (data: ProfileUpsert) =>
  profileFetch<Profile>("/profile", "PUT", data);

export const deleteProfile = () =>
  profileFetch<{ ok: boolean }>("/profile", "DELETE");

export const extractProfile = (session_id: string) =>
  profileFetch<ExtractOut>("/profile/extract", "POST", { session_id });
