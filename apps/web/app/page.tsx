"use client";

import Link from "next/link";
import { useState } from "react";
import { authRequest, fetchMe } from "@/lib/api";

export default function Home() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  async function handle(path: "/auth/signup" | "/auth/login") {
    setMessage("...");
    try {
      const token = await authRequest(path, email, password);
      localStorage.setItem("pf_token", token);
      const me = await fetchMe(token);
      setMessage(`Signed in as ${me.email} (plan: ${me.plan})`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-bold">PromptForge</h1>
      <Link href="/generate" className="text-blue-600 hover:underline">
        Try prompt generation →
      </Link>
      <Link href="/library" className="text-blue-600 hover:underline">
        My prompts →
      </Link>
      <input
        className="border rounded px-3 py-2 w-72"
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        className="border rounded px-3 py-2 w-72"
        placeholder="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <div className="flex gap-2">
        <button className="bg-black text-white rounded px-4 py-2" onClick={() => handle("/auth/signup")}>
          Sign up
        </button>
        <button className="border rounded px-4 py-2" onClick={() => handle("/auth/login")}>
          Log in
        </button>
      </div>
      {message && <p className="text-sm text-gray-600">{message}</p>}
    </main>
  );
}
