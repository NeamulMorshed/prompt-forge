"use client";

import { useState } from "react";
import { upsertProfile } from "@/lib/profile-api";
import type { ProfileUpsert } from "@/lib/profile-api";

interface Props {
  extractableSlots: Record<string, string>;
  isAuthenticated: boolean;
}

const CORE = new Set(["tone", "audience", "brand_name", "constraints"]);

function slotsToProfileUpsert(slots: Record<string, string>): ProfileUpsert {
  const core_context: Record<string, string> = {};
  const domainSlots: Record<string, string> = {};
  for (const [k, v] of Object.entries(slots)) {
    if (CORE.has(k)) core_context[k] = v;
    else domainSlots[k] = v;
  }
  return {
    core_context,
    domain_overrides: Object.keys(domainSlots).length ? { generated: domainSlots } : {},
  };
}

export function ProfileSavePrompt({ extractableSlots, isAuthenticated }: Props) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "dismissed" | "error">("idle");

  if (state === "dismissed" || state === "saved") return null;

  if (Object.keys(extractableSlots).length === 0) return null;

  if (state === "error") {
    return (
      <div className="text-sm text-red-500 border border-red-200 rounded-lg px-4 py-3 flex items-center gap-3">
        <span>Could not save defaults.</span>
        <button className="underline" onClick={() => setState("idle")}>Try again</button>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="text-sm text-gray-500 border rounded-lg px-4 py-3 bg-gray-50 flex items-center gap-3">
        <span>Save these as your defaults for next time?</span>
        <a href="/signup?next=/settings/profile" className="text-blue-600 underline">
          Create account →
        </a>
      </div>
    );
  }

  const previewKeys = Object.keys(extractableSlots).slice(0, 3).join(", ") || "your preferences";

  async function handleSave() {
    setState("saving");
    try {
      const data = slotsToProfileUpsert(extractableSlots);
      await upsertProfile(data);
      setState("saved");
    } catch {
      setState("error");
    }
  }

  function handleDismiss() {
    if (typeof window !== "undefined") {
      localStorage.setItem("pf_profile_save_dismissed", "1");
    }
    setState("dismissed");
  }

  if (state === "saving") {
    return <p className="text-sm text-gray-400 animate-pulse">Saving&hellip;</p>;
  }

  return (
    <div className="text-sm border rounded-lg px-4 py-3 bg-gray-50 flex flex-col gap-2">
      <p className="text-gray-700">
        Save <span className="font-medium">{previewKeys}</span> as your defaults for next time?
      </p>
      <div className="flex gap-3">
        <button
          className="bg-black text-white rounded px-4 py-1.5 text-sm"
          onClick={handleSave}
        >
          Save defaults
        </button>
        <button className="text-gray-400 text-sm underline" onClick={handleDismiss}>
          Not now
        </button>
        <a href="/settings/profile" className="text-gray-400 text-sm underline">
          Edit manually →
        </a>
      </div>
    </div>
  );
}
