"use client";
import { useEffect, useState } from "react";
import { listApiKeys, createApiKey, revokeApiKey, KeySummary, CreateKeyResponse } from "@/lib/api-keys-api";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<KeySummary[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyResult, setNewKeyResult] = useState<CreateKeyResponse | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      setKeys(await listApiKeys());
    } catch {
      setError("Failed to load keys");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate() {
    if (!newKeyName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const result = await createApiKey(newKeyName.trim());
      setNewKeyResult(result);
      setNewKeyName("");
      await load();
    } catch {
      setError("Failed to create key");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(keyId: string) {
    if (!confirm("Revoke this key? Any apps using it will stop working.")) return;
    try {
      await revokeApiKey(keyId);
      await load();
    } catch {
      setError("Failed to revoke key");
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">API Keys</h1>

      {loading && <p className="text-gray-400 text-sm mb-4">Loading…</p>}

      {newKeyResult && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded">
          <p className="font-semibold mb-2">Copy your key now — it won&apos;t be shown again.</p>
          <code className="block break-all text-sm bg-white border p-2 rounded select-all">
            {newKeyResult.key}
          </code>
          <button
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(newKeyResult.key);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              } catch {
                // clipboard unavailable
              }
            }}
            className="mt-2 text-sm text-blue-600 underline"
          >
            {copied ? "Copied!" : "Copy to clipboard"}
          </button>
        </div>
      )}

      <div className="flex gap-2 mb-8">
        <input
          type="text"
          placeholder="Key name (e.g. My App)"
          value={newKeyName}
          onChange={(e) => setNewKeyName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button
          onClick={handleCreate}
          disabled={creating || !newKeyName.trim()}
          className="px-4 py-2 bg-black text-white rounded text-sm disabled:opacity-50"
        >
          {creating ? "Creating…" : "Create Key"}
        </button>
      </div>

      {error && <p className="text-red-600 mb-4 text-sm">{error}</p>}

      {keys.length === 0 ? (
        <p className="text-gray-500 text-sm">No API keys yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="pb-2">Name</th>
              <th className="pb-2">Prefix</th>
              <th className="pb-2">Last used</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id} className="border-b">
                <td className="py-3">{k.name}</td>
                <td className="py-3 font-mono text-gray-500">{k.key_prefix}…</td>
                <td className="py-3 text-gray-500">
                  {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                </td>
                <td className="py-3">
                  <button
                    onClick={() => handleRevoke(k.id)}
                    className="text-red-600 hover:underline"
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
