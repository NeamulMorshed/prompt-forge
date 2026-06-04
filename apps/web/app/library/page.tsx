"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  listLibrary,
  getPromptGroup,
  labelVersion,
  deletePrompt,
  branchVersion,
} from "@/lib/library-api";
import type { PromptGroupOut, PromptGroupDetailOut } from "@/lib/library-api";

const DOMAIN_OPTIONS = [
  { value: "", label: "All domains" },
  { value: "marketing_content", label: "Marketing content" },
  { value: "writing_academic", label: "Academic writing" },
];

export default function LibraryPage() {
  const router = useRouter();
  const [noToken, setNoToken] = useState(() =>
    typeof window !== "undefined" ? !localStorage.getItem("pf_token") : false
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [domain, setDomain] = useState("");
  const [groups, setGroups] = useState<PromptGroupOut[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<PromptGroupDetailOut | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [branching, setBranching] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState<{ promptId: string; versionId: string; value: string } | null>(null);
  const labelInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (noToken) { setLoading(false); return; }
    fetchGroups();
  }, [domain, noToken]);

  useEffect(() => {
    if (editLabel && labelInputRef.current) {
      labelInputRef.current.focus();
    }
  }, [editLabel]);

  async function fetchGroups() {
    setLoading(true);
    setError(null);
    try {
      const data = await listLibrary(domain || undefined);
      setGroups(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleExpand(rootPromptId: string) {
    if (expanded === rootPromptId) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(rootPromptId);
    setDetail(null);
    setDetailLoading(true);
    try {
      const d = await getPromptGroup(rootPromptId);
      setDetail(d);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleBranch(versionId: string) {
    setBranching(versionId);
    try {
      const turn = await branchVersion(versionId);
      sessionStorage.setItem("pf_branch_turn", JSON.stringify(turn));
      router.push("/generate");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Branch failed");
    } finally {
      setBranching(null);
    }
  }

  async function handleDelete(promptId: string) {
    if (!window.confirm("Delete this prompt and all its versions? This cannot be undone.")) return;
    try {
      await deletePrompt(promptId);
      setGroups((g) => g.filter((x) => x.root_prompt_id !== promptId));
      if (expanded === promptId) { setExpanded(null); setDetail(null); }
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function handleSaveLabel() {
    if (!editLabel) return;
    try {
      await labelVersion(editLabel.promptId, editLabel.versionId, editLabel.value.trim() || null);
      setDetail((d) => {
        if (!d) return d;
        return {
          ...d,
          prompts: d.prompts.map((p) =>
            p.id === editLabel.promptId
              ? {
                  ...p,
                  versions: p.versions.map((v) =>
                    v.id === editLabel.versionId
                      ? { ...v, outcome_label: editLabel.value.trim() || null }
                      : v
                  ),
                }
              : p
          ),
        };
      });
    } catch { /* ignore */ }
    setEditLabel(null);
  }

  if (noToken) {
    return (
      <main className="min-h-screen flex items-center justify-center p-8">
        <p className="text-gray-500 text-sm">
          <a href="/" className="text-blue-600 underline">Log in</a> to view your prompt library.
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center p-8 bg-white">
      <div className="w-full max-w-2xl flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">My prompts</h1>
          <select
            className="border rounded px-3 py-1.5 text-sm"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          >
            {DOMAIN_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {loading && <p className="text-gray-400 text-sm animate-pulse">Loading&hellip;</p>}
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {!loading && !error && groups.length === 0 && (
          <p className="text-gray-400 text-sm">No prompts yet. <a href="/generate" className="underline">Generate one →</a></p>
        )}

        {groups.map((group) => (
          <div key={group.group_id} className="border rounded-lg overflow-hidden">
            <div
              className="flex items-start justify-between gap-3 p-4 cursor-pointer hover:bg-gray-50"
              onClick={() => handleExpand(group.root_prompt_id)}
            >
              <div className="flex flex-col gap-1 flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  {group.domain && (
                    <span className="text-xs bg-gray-100 rounded-full px-2 py-0.5 text-gray-500">
                      {group.domain.replaceAll("_", " ")}
                    </span>
                  )}
                  <span className="text-xs text-gray-400 bg-blue-50 rounded-full px-2 py-0.5">
                    v{group.version_count}
                  </span>
                  {group.latest_version.score !== null && (
                    <span className="text-xs text-gray-400">
                      {Math.round(group.latest_version.score)}/100
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-700 line-clamp-2 font-mono">
                  {group.latest_version.content_preview}
                </p>
                <p className="text-xs text-gray-400">
                  {new Date(group.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  className="text-xs border rounded px-3 py-1 hover:bg-gray-100"
                  onClick={(e) => { e.stopPropagation(); handleBranch(group.latest_version.id); }}
                  disabled={branching === group.latest_version.id}
                >
                  {branching === group.latest_version.id ? "Branching…" : "Branch →"}
                </button>
                <button
                  className="text-xs text-red-400 hover:text-red-600"
                  onClick={(e) => { e.stopPropagation(); handleDelete(group.root_prompt_id); }}
                >
                  Delete
                </button>
                <span className="text-gray-300">{expanded === group.root_prompt_id ? "▲" : "▼"}</span>
              </div>
            </div>

            {expanded === group.root_prompt_id && (
              <div className="border-t bg-gray-50 px-4 py-3 flex flex-col gap-3">
                {detailLoading && <p className="text-xs text-gray-400 animate-pulse">Loading versions&hellip;</p>}
                {detail && (() => {
                  let counter = 0;
                  return detail.prompts.flatMap((prompt) =>
                    prompt.versions.map((version) => {
                      counter++;
                      return (
                    <div key={version.id} className="flex items-start justify-between gap-3 border-b last:border-0 pb-3 last:pb-0">
                      <div className="flex flex-col gap-1 flex-1 min-w-0">
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <span>v{counter}</span>
                          <span>{new Date(version.created_at).toLocaleDateString()}</span>
                          {prompt.branched_from_version_id && (
                            <span className="bg-purple-50 text-purple-500 rounded-full px-2 py-0.5">branched</span>
                          )}
                        </div>
                        <p className="text-xs font-mono text-gray-600 line-clamp-2">{version.content.length > 120 ? version.content.slice(0, 120) + "…" : version.content}</p>
                        {editLabel?.versionId === version.id ? (
                          <div className="flex gap-2 mt-1">
                            <input
                              ref={labelInputRef}
                              className="border rounded px-2 py-0.5 text-xs flex-1"
                              value={editLabel.value}
                              onChange={(e) => setEditLabel({ ...editLabel, value: e.target.value })}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleSaveLabel();
                                if (e.key === "Escape") setEditLabel(null);
                              }}
                              placeholder="e.g. worked great for IG"
                            />
                            <button className="text-xs text-green-600" onClick={handleSaveLabel}>Save</button>
                            <button className="text-xs text-gray-400" onClick={() => setEditLabel(null)}>Cancel</button>
                          </div>
                        ) : (
                          <button
                            className="text-xs text-left text-gray-400 hover:text-gray-600 mt-1"
                            onClick={() => setEditLabel({ promptId: prompt.id, versionId: version.id, value: version.outcome_label ?? "" })}
                          >
                            {version.outcome_label ? `"${version.outcome_label}"` : "+ add label"}
                          </button>
                        )}
                      </div>
                      <button
                        className="text-xs border rounded px-3 py-1 hover:bg-gray-100 flex-shrink-0"
                        onClick={() => handleBranch(version.id)}
                        disabled={branching === version.id}
                      >
                        {branching === version.id ? "Branching…" : "Branch →"}
                      </button>
                    </div>
                      );
                    })
                  );
                })()}
              </div>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
