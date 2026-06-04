"use client";

import { useState, useEffect } from "react";
import { startGeneration, submitAnswer } from "@/lib/generate-api";
import type { TurnResponse, GenerationResult, Question } from "@/lib/generate-api";
import { DiscoveryChat } from "./components/DiscoveryChat";
import { PromptOutput } from "./components/PromptOutput";
import { ProfileSavePrompt } from "./components/ProfileSavePrompt";

type PageState =
  | { phase: "idle" }
  | { phase: "asking"; session_id: string; question: Question; question_count: number; profile_loaded: boolean }
  | { phase: "generating" }
  | {
      phase: "done";
      result: GenerationResult;
      suggest_profile_save: boolean;
      extractable_slots: Record<string, string>;
      session_id: string;
    }
  | { phase: "error"; message: string };

function readBranchTurn(): TurnResponse | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem("pf_branch_turn");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TurnResponse;
  } catch { return null; }
}

function initialPageState(branchTurn: TurnResponse | null): PageState {
  if (!branchTurn) return { phase: "idle" };
  if (branchTurn.status === "done" && branchTurn.result) {
    return {
      phase: "done",
      result: branchTurn.result,
      suggest_profile_save: branchTurn.suggest_profile_save,
      extractable_slots: branchTurn.extractable_slots,
      session_id: branchTurn.session_id,
    };
  }
  if (branchTurn.status === "needs_question" && branchTurn.question) {
    return {
      phase: "asking",
      session_id: branchTurn.session_id,
      question: branchTurn.question,
      question_count: 1,
      profile_loaded: branchTurn.profile_loaded,
    };
  }
  return { phase: "idle" };
}

export default function GeneratePage() {
  const [input, setInput] = useState(() => {
    const bt = readBranchTurn();
    return bt ? "(branched)" : "";
  });
  const [pageState, setPageState] = useState<PageState>(() => initialPageState(readBranchTurn()));
  const [profileDismissed] = useState(
    () => typeof window !== "undefined" && localStorage.getItem("pf_profile_save_dismissed") === "1"
  );
  const [isAuthenticated] = useState(
    () => typeof window !== "undefined" && !!localStorage.getItem("pf_token")
  );
  const [modelTarget, setModelTarget] = useState<string>("gemini-2.0-flash");
  const isPro = typeof window !== "undefined" && localStorage.getItem("pf_plan") === "pro";

  useEffect(() => {
    sessionStorage.removeItem("pf_branch_turn");
  }, []);

  function applyTurn(turn: TurnResponse, currentCount: number) {
    if (turn.status === "done" && turn.result) {
      setPageState({
        phase: "done",
        result: turn.result,
        suggest_profile_save: turn.suggest_profile_save,
        extractable_slots: turn.extractable_slots,
        session_id: turn.session_id,
      });
    } else if (turn.status === "needs_question" && turn.question) {
      setPageState({
        phase: "asking",
        session_id: turn.session_id,
        question: turn.question,
        question_count: currentCount,
        profile_loaded: turn.profile_loaded,
      });
    }
  }

  async function handleStart() {
    if (!input.trim()) return;
    setPageState({ phase: "generating" });
    try {
      const turn = await startGeneration(input.trim(), false, isPro ? modelTarget : undefined);
      applyTurn(turn, 1);
    } catch (e) {
      setPageState({ phase: "error", message: e instanceof Error ? e.message : "Error" });
    }
  }

  async function handleStartFresh() {
    if (!input.trim()) return;
    setPageState({ phase: "generating" });
    try {
      const turn = await startGeneration(input.trim(), true, isPro ? modelTarget : undefined);
      applyTurn(turn, 1);
    } catch (e) {
      setPageState({ phase: "error", message: e instanceof Error ? e.message : "Error" });
    }
  }

  async function handleAnswer(answer: string) {
    if (pageState.phase !== "asking") return;
    const { session_id, question, question_count } = pageState;
    setPageState({ phase: "generating" });
    try {
      const turn = await submitAnswer(session_id, question.slot_id, answer);
      applyTurn(turn, question_count + 1);
    } catch (e) {
      setPageState({ phase: "error", message: e instanceof Error ? e.message : "Error" });
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 p-8 bg-white">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">PromptForge</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Describe what you want. We&apos;ll ask a few questions, then hand you a prompt that works.
        </p>
      </div>

      {pageState.phase === "idle" && (
        <div className="w-full max-w-xl flex flex-col gap-3">
          <textarea
            className="border rounded-lg px-4 py-3 text-sm w-full resize-none focus:outline-none focus:ring-2 focus:ring-black"
            rows={3}
            placeholder="e.g. 'I need a LinkedIn post announcing our new AI product to startup founders'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.metaKey) handleStart();
            }}
          />
          {isPro && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
              <select
                value={modelTarget}
                onChange={(e) => setModelTarget(e.target.value)}
                className="border rounded px-3 py-2 text-sm w-full max-w-xs"
              >
                <option value="gemini-2.0-flash">Gemini Flash (free)</option>
                <option value="gpt-4o">GPT-4o (Pro)</option>
                <option value="claude-sonnet-4-6">Claude Sonnet (Pro)</option>
              </select>
            </div>
          )}
          <button
            className="bg-black text-white rounded-lg px-6 py-3 font-medium text-sm disabled:opacity-40 self-end"
            disabled={!input.trim()}
            onClick={handleStart}
          >
            Generate prompt &rarr;
          </button>
        </div>
      )}

      {pageState.phase === "generating" && (
        <p className="text-gray-400 text-sm animate-pulse">Working on it&hellip;</p>
      )}

      {pageState.phase === "asking" && (
        <>
          {pageState.profile_loaded && (
            <p className="text-xs text-gray-400 bg-gray-50 border rounded-full px-3 py-1">
              Using My defaults &middot;{" "}
              <button className="underline" onClick={handleStartFresh}>
                clear
              </button>
            </p>
          )}
          <DiscoveryChat
            question={pageState.question}
            onAnswer={handleAnswer}
            questionNumber={pageState.question_count}
          />
        </>
      )}

      {pageState.phase === "done" && (
        <div className="w-full max-w-2xl flex flex-col gap-6">
          <PromptOutput result={pageState.result} />
          {pageState.suggest_profile_save && !profileDismissed && (
            <ProfileSavePrompt
              extractableSlots={pageState.extractable_slots}
              isAuthenticated={isAuthenticated}
            />
          )}
        </div>
      )}

      {pageState.phase === "error" && (
        <div className="text-red-500 text-sm">
          Error: {pageState.message}
          <button className="ml-3 underline" onClick={() => setPageState({ phase: "idle" })}>
            Try again
          </button>
        </div>
      )}

      {pageState.phase !== "idle" && (
        <button
          className="text-xs text-gray-400 underline"
          onClick={() => {
            setPageState({ phase: "idle" });
            setInput("");
          }}
        >
          Start over
        </button>
      )}
    </main>
  );
}
