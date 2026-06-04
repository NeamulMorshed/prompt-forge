import json
from dataclasses import dataclass, field

from app.llm.router import LLMRouter
from app.pipeline.assembler import ContextObject

_RUBRIC: dict[str, dict] = {
    "clarity":       {"weight": 0.20, "gated": True,  "threshold": 6},
    "completeness":  {"weight": 0.18, "gated": True,  "threshold": 6},
    "richness":      {"weight": 0.15, "gated": False},
    "actionability": {"weight": 0.17, "gated": True,  "threshold": 6},
    "goal_align":    {"weight": 0.20, "gated": True,  "threshold": 6},
    "ai_perf":       {"weight": 0.10, "gated": False},
}

_JUDGE_SYSTEM = (
    "You are a prompt quality evaluator. Rate the following prompt on these dimensions (1–10 each):\n"
    "- clarity: how clearly written and unambiguous\n"
    "- completeness: all necessary instructions present\n"
    "- richness: depth of context provided\n"
    "- actionability: how directly actionable for an LLM\n"
    "- goal_align: how well aligned with the stated goal\n"
    "- ai_perf: likelihood of producing high-quality AI output\n"
    "Return JSON only: "
    '{"clarity":int,"completeness":int,"richness":int,"actionability":int,"goal_align":int,"ai_perf":int,"suggestions":[str,str]}'
)


@dataclass
class ScoreResult:
    composite: float
    scored: bool = True
    dimensions: dict[str, float] = field(default_factory=dict)
    gate_failures: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def score(prompt: str, ctx: ContextObject, router: LLMRouter) -> ScoreResult:
    goal_info = ctx.slots.get("goal")
    goal_text = goal_info.value if goal_info else "not specified"
    user_msg = f"Domain: {ctx.domain}\nGoal: {goal_text}\n\nPROMPT TO EVALUATE:\n{prompt}"
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    result = router.complete("evaluate", messages)
    try:
        data = json.loads(result.text)
    except json.JSONDecodeError:
        return ScoreResult(composite=50.0, scored=False, suggestions=["Score unavailable — LLM evaluator not configured."])

    composite = 0.0
    gate_failures: list[str] = []
    dimensions: dict[str, float] = {}
    for dim, cfg in _RUBRIC.items():
        raw = float(data.get(dim, 5))
        raw = max(1.0, min(10.0, raw))
        dimensions[dim] = raw
        composite += (raw / 10.0) * cfg["weight"] * 100
        if cfg.get("gated") and raw < cfg.get("threshold", 6):
            gate_failures.append(dim)

    return ScoreResult(
        composite=round(composite, 1),
        dimensions=dimensions,
        gate_failures=gate_failures,
        suggestions=data.get("suggestions", []),
    )
