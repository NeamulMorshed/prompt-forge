import json
from dataclasses import dataclass

from app.llm.router import LLMRouter
from app.pipeline.ccs import needs_discovery
from app.pipeline.crs_loader import Slot

MAX_QUESTIONS = 5


@dataclass
class Question:
    slot_id: str
    question: str
    chips: list[str]
    allow_freetext: bool


def next_question(
    slots: list[Slot],
    filled: dict[str, str],
    history: list[dict],
    questions_asked: int,
    router: LLMRouter,
) -> Question | None:
    if questions_asked >= MAX_QUESTIONS:
        return None
    if not needs_discovery(slots, filled):
        return None

    # Layer 1: deterministic — pick highest-weight unfilled slot (required slots get a boost)
    candidates = [s for s in slots if not filled.get(s.id)]
    if not candidates:
        return None
    top = max(candidates, key=lambda s: s.weight * (1.2 if s.required else 1.0))

    # Layer 2: LLM phrases the question naturally
    recent_context = json.dumps(history[-4:]) if history else "[]"
    phrase_prompt = (
        f"You are helping collect context for a prompt-generation tool.\n"
        f"Prior conversation: {recent_context}\n"
        f"Ask the user naturally about: \"{top.hint}\"\n"
        f"Provide 3-4 short answer chips. "
        f'Return JSON only: {{"question": str, "chips": [str, ...], "allow_freetext": bool}}'
    )
    result = router.complete("phrase_q", [{"role": "user", "content": phrase_prompt}])
    try:
        data = json.loads(result.text)
        return Question(
            slot_id=top.id,
            question=str(data["question"]),
            chips=list(data.get("chips", [])),
            allow_freetext=bool(data.get("allow_freetext", True)),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return Question(slot_id=top.id, question=top.hint, chips=[], allow_freetext=True)


def apply_answer(slot_id: str, answer: str, filled_slots: dict[str, str]) -> dict[str, str]:
    return {**filled_slots, slot_id: answer}
