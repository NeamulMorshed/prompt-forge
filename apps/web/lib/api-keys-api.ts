const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("pf_token") : null;
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

export interface KeySummary {
  id: string;
  name: string;
  key_prefix: string;
  rate_limit_per_minute: number;
  created_at: string;
  last_used_at: string | null;
}

export interface CreateKeyResponse {
  id: string;
  name: string;
  key: string;       // raw key — shown once
  key_prefix: string;
  created_at: string;
}

export async function listApiKeys(): Promise<KeySummary[]> {
  const res = await fetch(`${API_BASE}/v1/keys`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch keys");
  const data = await res.json();
  return data.keys;
}

export async function createApiKey(name: string): Promise<CreateKeyResponse> {
  const res = await fetch(`${API_BASE}/v1/keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error("Failed to create key");
  return res.json();
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/v1/keys/${keyId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("Failed to revoke key");
}
