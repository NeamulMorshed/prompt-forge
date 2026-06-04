"use client";

import { useEffect, useState } from "react";
import {
  createWorkspace,
  getMyWorkspace,
  inviteMember,
  leaveWorkspace,
  listMembers,
  Workspace,
  WorkspaceMember,
} from "@/lib/workspace-api";

export default function WorkspacePage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const ws = await getMyWorkspace();
        setWorkspace(ws);
        if (ws) {
          const m = await listMembers();
          setMembers(m);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const ws = await createWorkspace(newName);
      setWorkspace(ws);
      setMembers(await listMembers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await inviteMember(inviteEmail);
      setInviteEmail("");
      setMembers(await listMembers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  };

  const handleLeave = async () => {
    if (!confirm("Leave this workspace?")) return;
    try {
      await leaveWorkspace();
      setWorkspace(null);
      setMembers([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  };

  if (loading) return <div className="p-4">Loading...</div>;

  return (
    <main className="p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Workspace</h1>
      {error && <p className="text-red-600 mb-4 text-sm">{error}</p>}

      {!workspace ? (
        <form onSubmit={handleCreate} className="space-y-4">
          <p className="text-gray-600">You are not in a workspace yet.</p>
          <div>
            <label className="block text-sm font-medium mb-1">Workspace name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. ACME Corp"
              className="border rounded px-3 py-2 w-full"
              required
            />
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
            Create workspace
          </button>
        </form>
      ) : (
        <div className="space-y-6">
          <div className="border rounded p-4">
            <h2 className="text-xl font-semibold">{workspace.name}</h2>
            <p className="text-sm text-gray-600">Seats: {workspace.seats}</p>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-3">Members</h3>
            <div className="space-y-2">
              {members.map((m) => (
                <div key={m.user_id} className="flex justify-between border rounded px-3 py-2 text-sm">
                  <span>{m.email}</span>
                  <span className="text-gray-500 capitalize">{m.role}</span>
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={handleInvite} className="space-y-2">
            <h3 className="text-lg font-semibold">Invite member</h3>
            <div className="flex gap-2">
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@example.com"
                className="border rounded px-3 py-2 flex-1"
                required
              />
              <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
                Invite
              </button>
            </div>
          </form>

          <button onClick={handleLeave} className="text-red-600 text-sm hover:underline">
            Leave workspace
          </button>
        </div>
      )}
    </main>
  );
}
