"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getProfile, upsertProfile, deleteProfile, type Profile, type ProfileUpsert } from "@/lib/profile-api";

const CORE_FIELDS = ["tone", "audience", "brand_name", "constraints"];
const DOMAINS = [
  { value: "marketing_content", label: "Marketing content" },
  { value: "writing_academic", label: "Academic writing" },
];

export default function ProfilesPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editMode, setEditMode] = useState<"core" | "domain">("core");

  // Core context fields
  const [tone, setTone] = useState("");
  const [audience, setAudience] = useState("");
  const [brandName, setBrandName] = useState("");
  const [constraints, setConstraints] = useState("");

  // Domain overrides
  const [selectedDomain, setSelectedDomain] = useState("marketing_content");
  const [domainOverrides, setDomainOverrides] = useState<Record<string, string>>({});

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProfile();
      setProfile(data);
      if (data) {
        setTone(data.core_context?.tone || "");
        setAudience(data.core_context?.audience || "");
        setBrandName(data.core_context?.brand_name || "");
        setConstraints(data.core_context?.constraints || "");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleSaveCore = async () => {
    setError(null);
    try {
      const core_context: Record<string, string> = {};
      if (tone) core_context.tone = tone;
      if (audience) core_context.audience = audience;
      if (brandName) core_context.brand_name = brandName;
      if (constraints) core_context.constraints = constraints;

      const data = await upsertProfile({
        core_context,
        domain_overrides: profile?.domain_overrides || {},
      });
      setProfile(data);
      setIsEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const handleSaveDomain = async () => {
    setError(null);
    try {
      const newOverrides = { ...profile?.domain_overrides || {} };
      if (Object.keys(domainOverrides).length > 0) {
        newOverrides[selectedDomain] = domainOverrides;
      } else {
        delete newOverrides[selectedDomain];
      }

      const data = await upsertProfile({
        core_context: profile?.core_context || {},
        domain_overrides: newOverrides,
      });
      setProfile(data);
      setDomainOverrides({});
      setIsEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete your default profile?")) return;
    setError(null);
    try {
      await deleteProfile();
      setProfile(null);
      setTone("");
      setAudience("");
      setBrandName("");
      setConstraints("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center p-8">
        <p className="text-gray-500">Loading...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold">My Default Profile</h1>
          <Link href="/generate" className="text-blue-600 hover:underline text-sm">
            ← Back to generate
          </Link>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        {!profile ? (
          <div className="bg-gray-50 rounded p-6 border border-gray-200">
            <p className="text-gray-600 mb-4">
              Create a default profile to auto-fill your usual preferences.
            </p>
            <button
              onClick={() => {
                setIsEditing(true);
                setEditMode("core");
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Create profile
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Core Context Section */}
            <div className="bg-white border rounded p-6">
              <h2 className="text-lg font-semibold mb-4">Core context</h2>
              <div className="space-y-3">
                {profile.core_context?.tone && (
                  <div>
                    <p className="text-sm text-gray-600">Tone</p>
                    <p className="font-medium">{profile.core_context.tone}</p>
                  </div>
                )}
                {profile.core_context?.audience && (
                  <div>
                    <p className="text-sm text-gray-600">Audience</p>
                    <p className="font-medium">{profile.core_context.audience}</p>
                  </div>
                )}
                {profile.core_context?.brand_name && (
                  <div>
                    <p className="text-sm text-gray-600">Brand name</p>
                    <p className="font-medium">{profile.core_context.brand_name}</p>
                  </div>
                )}
                {profile.core_context?.constraints && (
                  <div>
                    <p className="text-sm text-gray-600">Constraints</p>
                    <p className="font-medium">{profile.core_context.constraints}</p>
                  </div>
                )}
              </div>
              {isEditing && editMode === "core" ? (
                <div className="mt-4 space-y-3 pt-4 border-t">
                  <input
                    type="text"
                    placeholder="Tone"
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Audience"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Brand name"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Constraints"
                    value={constraints}
                    onChange={(e) => setConstraints(e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={handleSaveCore}
                      className="bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="border rounded px-3 py-2 text-sm hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setIsEditing(true);
                    setEditMode("core");
                  }}
                  className="text-blue-600 hover:underline text-sm mt-4"
                >
                  Edit
                </button>
              )}
            </div>

            {/* Domain Overrides Section */}
            <div className="bg-white border rounded p-6">
              <h2 className="text-lg font-semibold mb-4">Domain overrides</h2>
              {Object.keys(profile.domain_overrides || {}).length === 0 ? (
                <p className="text-gray-600 text-sm mb-4">No domain-specific overrides yet.</p>
              ) : (
                <div className="space-y-4 mb-4">
                  {Object.entries(profile.domain_overrides).map(([domain, slots]) => (
                    <div key={domain} className="bg-gray-50 p-3 rounded">
                      <p className="text-sm font-medium text-gray-700 mb-2">{domain.replace(/_/g, " ")}</p>
                      <div className="space-y-1">
                        {Object.entries(slots).map(([key, value]) => (
                          <p key={key} className="text-xs text-gray-600">
                            <span className="font-medium">{key}:</span> {value}
                          </p>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {isEditing && editMode === "domain" ? (
                <div className="bg-gray-50 p-4 rounded space-y-3 pt-4 border-t mt-4">
                  <select
                    value={selectedDomain}
                    onChange={(e) => {
                      setSelectedDomain(e.target.value);
                      setDomainOverrides(profile.domain_overrides?.[e.target.value] || {});
                    }}
                    className="w-full border rounded px-3 py-2 text-sm"
                  >
                    {DOMAINS.map((d) => (
                      <option key={d.value} value={d.value}>
                        {d.label}
                      </option>
                    ))}
                  </select>

                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-2">
                      Add field (optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., channel, success_metric"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          const key = e.currentTarget.value.trim();
                          if (key) {
                            setDomainOverrides((prev) => ({ ...prev, [key]: "" }));
                            e.currentTarget.value = "";
                          }
                        }
                      }}
                      className="w-full border rounded px-3 py-2 text-sm"
                    />
                    <p className="text-xs text-gray-500 mt-1">Press Enter to add field</p>
                  </div>

                  <div className="space-y-2">
                    {Object.entries(domainOverrides).map(([key, value]) => (
                      <div key={key} className="flex gap-2">
                        <input
                          type="text"
                          disabled
                          value={key}
                          className="w-1/3 border rounded px-3 py-2 text-sm bg-gray-100"
                        />
                        <input
                          type="text"
                          placeholder="Value"
                          value={value}
                          onChange={(e) =>
                            setDomainOverrides((prev) => ({ ...prev, [key]: e.target.value }))
                          }
                          className="w-2/3 border rounded px-3 py-2 text-sm"
                        />
                        <button
                          onClick={() =>
                            setDomainOverrides((prev) => {
                              const next = { ...prev };
                              delete next[key];
                              return next;
                            })
                          }
                          className="text-red-600 hover:underline text-sm"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={handleSaveDomain}
                      className="bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="border rounded px-3 py-2 text-sm hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setIsEditing(true);
                    setEditMode("domain");
                    setDomainOverrides(profile.domain_overrides?.[selectedDomain] || {});
                  }}
                  className="text-blue-600 hover:underline text-sm"
                >
                  Edit
                </button>
              )}
            </div>

            {/* Delete */}
            <div className="pt-4 border-t">
              <button
                onClick={handleDelete}
                className="text-red-600 hover:underline text-sm"
              >
                Delete profile
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
