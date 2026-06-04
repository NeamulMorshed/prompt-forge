"use client";

import { useState } from "react";
import { editModule, EditModuleResponse, ScoreOut } from "@/lib/generate-api";

const MODULE_LABELS: Record<string, string> = {
  role: "Role",
  objective: "Objective",
  context: "Context",
  task: "Task",
  format: "Format",
  patterns: "Patterns",
  examples: "Examples",
  reasoning: "Reasoning",
  guardrails: "Guardrails",
};

interface Props {
  promptVersionId: string;
  modules: Record<string, string>;
  onUpdated: (newVersionId: string, newScore: ScoreOut, fullPrompt: string) => void;
}

export function ModuleEditor({ promptVersionId, modules, onUpdated }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async (moduleName: string) => {
    const text = drafts[moduleName];
    if (!text) return;
    setSaving(moduleName);
    setError(null);
    try {
      const result: EditModuleResponse = await editModule(promptVersionId, moduleName, text);
      onUpdated(result.new_prompt_version_id, result.score, result.full_prompt);
      setExpanded(null);
      setDrafts((prev) => { const d = { ...prev }; delete d[moduleName]; return d; });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="mt-6 border-t pt-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Edit by module</h3>
      {error && <p className="text-red-600 text-xs mb-2">{error}</p>}
      <div className="space-y-2">
        {Object.entries(modules).filter(([, v]) => v.trim()).map(([name, text]) => (
          <div key={name} className="border rounded">
            <button
              className="w-full text-left px-3 py-2 text-sm font-medium flex justify-between items-center hover:bg-gray-50"
              onClick={() => {
                setExpanded(expanded === name ? null : name);
                if (!drafts[name]) setDrafts((prev) => ({ ...prev, [name]: text }));
              }}
            >
              <span>{MODULE_LABELS[name] ?? name}</span>
              <span className="text-gray-400">{expanded === name ? "▲" : "▼"}</span>
            </button>
            {expanded === name && (
              <div className="px-3 pb-3">
                <textarea
                  value={drafts[name] ?? text}
                  onChange={(e) => setDrafts((prev) => ({ ...prev, [name]: e.target.value }))}
                  rows={4}
                  className="w-full border rounded px-2 py-1 text-sm font-mono mt-1"
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => handleSave(name)}
                    disabled={saving === name}
                    className="bg-blue-600 text-white text-xs px-3 py-1 rounded disabled:opacity-50"
                  >
                    {saving === name ? "Saving..." : "Save & re-score"}
                  </button>
                  <button
                    onClick={() => {
                      setExpanded(null);
                      setDrafts((prev) => { const d = { ...prev }; delete d[name]; return d; });
                    }}
                    className="text-gray-500 text-xs px-2 py-1"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
