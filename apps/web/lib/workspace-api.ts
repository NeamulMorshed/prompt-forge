const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function authHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("pf_token") : null;
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

export interface Workspace {
  id: string;
  name: string;
  seats: number;
}

export interface WorkspaceMember {
  user_id: string;
  email: string;
  role: string;
  joined_at: string;
}

export async function getMyWorkspace(): Promise<Workspace | null> {
  const res = await fetch(`${API_BASE}/workspace/me`, { headers: authHeaders() });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to get workspace");
  return res.json();
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const res = await fetch(`${API_BASE}/workspace`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error("Failed to create workspace");
  return res.json();
}

export async function listMembers(): Promise<WorkspaceMember[]> {
  const res = await fetch(`${API_BASE}/workspace/members`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to list members");
  return res.json();
}

export async function inviteMember(email: string, role: string = "member"): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/invite`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ email, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to invite" }));
    throw new Error((err as { detail?: string }).detail ?? "Failed to invite");
  }
}

export async function leaveWorkspace(): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/leave`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to leave workspace");
}
