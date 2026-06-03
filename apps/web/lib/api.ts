const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function authRequest(
  path: "/auth/signup" | "/auth/login",
  email: string,
  password: string,
): Promise<string> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Request failed");
  }
  const data = await res.json();
  return data.access_token as string;
}

export async function fetchMe(token: string) {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch user");
  return res.json();
}
