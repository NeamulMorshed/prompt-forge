"use client";

import { useState } from "react";
import type { Question } from "@/lib/generate-api";

interface Props {
  question: Question;
  onAnswer: (answer: string) => void;
  questionNumber: number;
}

export function DiscoveryChat({ question, onAnswer, questionNumber }: Props) {
  const [freetext, setFreetext] = useState("");

  return (
    <div className="w-full max-w-xl flex flex-col gap-4">
      <p className="text-xs text-gray-400 uppercase tracking-wide">
        Question {questionNumber} of 5 max
      </p>
      <p className="text-lg font-medium text-gray-900">{question.question}</p>
      <div className="flex flex-wrap gap-2">
        {question.chips.map((chip) => (
          <button
            key={chip}
            className="border rounded-full px-4 py-1.5 text-sm hover:bg-gray-100 transition-colors"
            onClick={() => onAnswer(chip)}
          >
            {chip}
          </button>
        ))}
      </div>
      {question.allow_freetext && (
        <div className="flex gap-2">
          <input
            className="border rounded px-3 py-2 flex-1 text-sm"
            placeholder="Or type your own answer…"
            value={freetext}
            onChange={(e) => setFreetext(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && freetext.trim()) {
                onAnswer(freetext.trim());
                setFreetext("");
              }
            }}
          />
          <button
            className="bg-black text-white rounded px-4 py-2 text-sm disabled:opacity-40"
            disabled={!freetext.trim()}
            onClick={() => {
              onAnswer(freetext.trim());
              setFreetext("");
            }}
          >
            Send
          </button>
        </div>
      )}
      <button
        className="text-xs text-gray-400 underline self-start"
        onClick={() => onAnswer("skip")}
      >
        Skip this question &rarr;
      </button>
    </div>
  );
}
