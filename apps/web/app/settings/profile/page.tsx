"use client";

import { useEffect, useState } from "react";
import { getProfile, upsertProfile } from "@/lib/profile-api";

const DOMAINS = ["marketing_content", "writing_academic"] as const;

const DOMAIN_LABELS: Record<string, string> = {
  marketing_content: "Marketing content",
  writing_academic: "Academic writing",
};

const DOMAIN_SLOTS: Record<string, { id: string; label: string }[]> = {
  marketing_content: [
    { id: "channel", label: "Default channel (e.g. LinkedIn, email)" },
    { id: "success", label: "How you measure success" },
    { id: "goal", label: "Default goal" },
  ],
  writing_academic: [
    { id: "level", label: "Academic level (e.g. PhD, undergraduate)" },
    { id: "sources", label: "Citation style (e.g. APA 7th ed)" },
  ],
};

type CoreFields = { tone: string; audience: string; brand_name: string; constraints: string };

export default function ProfileSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [noToken, setNoToken] = useState(false);

  const [core, setCore] = useState<CoreFields>({ tone: "", audience: "", brand_name: "", constraints: "" });
  const [domainSlots, setDomainSlots] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    const token = localStorage.getItem("pf_token");
    if (!token) {
      setNoToken(true);
      setLoading(false);
      return;
    }
    getProfile()
      .then((profile) => {
        if (profile) {
          setCore({
            tone: profile.core_context.tone ?? "",
            audience: profile.core_context.audience ?? "",
            brand_name: profile.core_context.brand_name ?? "",
            constraints: profile.core_context.constraints ?? "",
          });
          setDomainSlots(
            Object.fromEntries(
              DOMAINS.map((d) => [d, profile.domain_overrides[d] ?? {}])
            )
          );
        }
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      const clean_core: Record<string, string> = {};
      for (const [k, v] of Object.entries(core)) {
        if (v.trim()) clean_core[k] = v.trim();
      }
      const domain_overrides: Record<string, Record<string, string>> = {};
      for (const domain of DOMAINS) {
        const slots = domainSlots[domain] ?? {};
        const cleaned: Record<string, string> = {};
        for (const [k, v] of Object.entries(slots)) {
          if (v?.trim()) cleaned[k] = v.trim();
        }
        if (Object.keys(cleaned).length) domain_overrides[domain] = cleaned;
      }
      await upsertProfile({ core_context: clean_core, domain_overrides });
      setToast("Profile saved");
      setTimeout(() => setToast(null), 2500);
    } catch {
      setToast("Save failed — are you logged in?");
      setTimeout(() => setToast(null), 3000);
    } finally {
      setSaving(false);
    }
  }

  if (noToken) {
    return (
      <main className="min-h-screen flex items-center justify-center p-8">
        <p className="text-gray-500 text-sm">
          <a href="/login" className="text-blue-600 underline">Log in</a> to manage your profile.
        </p>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center p-8">
        <p className="text-gray-400 text-sm animate-pulse">Loading&hellip;</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center p-8 bg-white">
      <div className="w-full max-w-xl flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My defaults</h1>
          <p className="text-gray-500 text-sm mt-1">
            Pre-fill these on every generation so you never re-answer the same questions.
          </p>
        </div>

        {/* Core brand layer */}
        <section className="flex flex-col gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">Brand defaults</h2>
          {(
            [
              { id: "tone", label: "Tone / voice", placeholder: "e.g. playful and bold" },
              { id: "audience", label: "Typical audience", placeholder: "e.g. indie hackers and early-stage founders" },
              { id: "brand_name", label: "Brand name", placeholder: "e.g. Acme Inc" },
              { id: "constraints", label: "Constraints", placeholder: "e.g. no jargon, max 300 words" },
            ] as { id: keyof CoreFields; label: string; placeholder: string }[]
          ).map(({ id, label, placeholder }) => (
            <label key={id} className="flex flex-col gap-1">
              <span className="text-sm text-gray-700">{label}</span>
              <input
                className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                placeholder={placeholder}
                value={core[id]}
                onChange={(e) => setCore((c) => ({ ...c, [id]: e.target.value }))}
              />
            </label>
          ))}
        </section>

        {/* Domain overrides */}
        {DOMAINS.map((domain) => (
          <section key={domain} className="flex flex-col gap-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">
              {DOMAIN_LABELS[domain]}
            </h2>
            {DOMAIN_SLOTS[domain].map(({ id, label }) => (
              <label key={id} className="flex flex-col gap-1">
                <span className="text-sm text-gray-700">{label}</span>
                <input
                  className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  value={domainSlots[domain]?.[id] ?? ""}
                  onChange={(e) =>
                    setDomainSlots((prev) => ({
                      ...prev,
                      [domain]: { ...(prev[domain] ?? {}), [id]: e.target.value },
                    }))
                  }
                />
              </label>
            ))}
          </section>
        ))}

        <button
          className="bg-black text-white rounded-lg px-6 py-3 font-medium text-sm disabled:opacity-40 self-start"
          disabled={saving}
          onClick={handleSave}
        >
          {saving ? "Saving…" : "Save profile"}
        </button>

        {toast && (
          <p className={`text-sm ${toast.includes("failed") ? "text-red-500" : "text-green-600"}`}>
            {toast}
          </p>
        )}
      </div>
    </main>
  );
}
