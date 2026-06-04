"use client";

import { useState } from "react";
import Link from "next/link";
import type { GenerationResult } from "@/lib/generate-api";
import { runPrompt, ratePrompt } from "@/lib/generate-api";

interface Props {
  result: GenerationResult;
}

export function PromptOutput({ result }: Props) {
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<string | null>(null);
  const [rated, setRated] = useState<1 | -1 | null>(null);

  async function handleCopy() {
    await navigator.clipboard.writeText(result.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleRun() {
    setRunning(true);
    try {
      const { output: text } = await runPrompt(result.prompt_version_id);
      setOutput(text);
    } catch (e) {
      setOutput(e instanceof Error ? e.message : "Error running prompt");
    } finally {
      setRunning(false);
    }
  }

  async function handleRate(rating: 1 | -1) {
    setRated(rating);
    await ratePrompt(result.prompt_version_id, rating).catch(() => null);
  }

  const score = result.score;

  return (
    <div className="w-full max-w-2xl flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="h-2 flex-1 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full transition-all"
            style={{ width: `${score.composite}%` }}
          />
        </div>
        <span className="text-sm font-semibold text-gray-700">
          {Math.round(score.composite)}/100
        </span>
      </div>

      {score.suggestions.length > 0 && (
        <ul className="text-sm text-gray-500 list-disc pl-5 space-y-1">
          {score.suggestions.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      )}

      <pre className="whitespace-pre-wrap bg-gray-50 border rounded-lg p-4 text-sm font-mono leading-relaxed">
        {result.prompt}
      </pre>

      <div className="flex gap-3 flex-wrap">
        <button
          className="bg-black text-white rounded px-5 py-2 text-sm font-medium"
          onClick={handleCopy}
        >
          {copied ? "Copied!" : "Copy prompt"}
        </button>
        <button
          className="border rounded px-5 py-2 text-sm font-medium disabled:opacity-40"
          onClick={handleRun}
          disabled={running}
        >
          {running ? "Running…" : "Run it →"}
        </button>
      </div>

      {output && (
        <div className="border rounded-lg p-4 bg-white">
          <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">AI output</p>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{output}</p>
        </div>
      )}

      {output && rated === null && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">Did this achieve your goal?</span>
          <button className="text-2xl hover:scale-110 transition-transform" onClick={() => handleRate(1)}>&#128077;</button>
          <button className="text-2xl hover:scale-110 transition-transform" onClick={() => handleRate(-1)}>&#128078;</button>
        </div>
      )}
      {rated !== null && (
        <p className="text-sm text-gray-400">Thanks for the feedback &mdash; it helps improve PromptForge.</p>
      )}
      <Link
        href="/library"
        className="text-xs text-gray-400 underline self-start"
      >
        View all my prompts →
      </Link>
    </div>
  );
}
