import json
import uuid

from sqlalchemy.orm import Session as DBSession

from app.db.models import PromptVersion
from app.llm.router import LLMRouter
from app.pipeline.evaluator import ScoreResult
from app.pipeline.module_editor import edit_module

_AUTO_IMPROVE_THRESHOLD = 85.0

_JUDGE_SYSTEM = (
    "You are a prompt output evaluator. Given a prompt and the LLM output it produced, "
    "identify the weakest area.\n"
    "Return JSON only: "
    '{"quality": int (1-10), "weakest_module": str | null, "fix_instruction": str}\n'
    "weakest_module must be one of: role, objective, context, task, format, patterns, examples, reasoning, guardrails, null\n"
    "quality: 1=terrible output, 10=perfect output\n"
    "fix_instruction: specific instruction to rewrite the weakest module to improve the output"
)

_VALID_MODULES = {
    "role", "objective", "context", "task", "format",
    "patterns", "examples", "reasoning", "guardrails",
}


def _judge_output(prompt: str, output: str, router: LLMRouter) -> dict:
    user_msg = f"PROMPT:\n{prompt}\n\nLLM OUTPUT:\n{output}"
    result = router.complete("evaluate", [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {"role": "user", "content": user_msg},
    ])
    try:
        data = json.loads(result.text)
        quality = max(1, min(10, int(data.get("quality", 5))))
        module = data.get("weakest_module")
        if module not in _VALID_MODULES:
            module = None
        return {
            "quality": quality,
            "weakest_module": module,
            "fix_instruction": data.get("fix_instruction", ""),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"quality": 5, "weakest_module": None, "fix_instruction": ""}


def _weakest_module(dimensions: dict[str, float]) -> str:
    return min(dimensions, key=lambda k: dimensions[k])


def auto_improve(
    version_id: uuid.UUID,
    router: LLMRouter,
    db: DBSession,
) -> tuple[PromptVersion, ScoreResult, str | None]:
    """
    Returns (version, score_result, rewritten_module_name | None).
    Returns existing version unchanged when score already >= threshold.
    """
    version = db.get(PromptVersion, version_id)
    if version is None:
        raise ValueError(f"PromptVersion {version_id} not found")

    current_score_json = version.score_json or {}
    composite = float(current_score_json.get("composite", 0))
    dimensions = current_score_json.get("dimensions", {})

    if composite >= _AUTO_IMPROVE_THRESHOLD:
        score_result = ScoreResult(
            composite=composite,
            dimensions=dimensions,
            suggestions=current_score_json.get("suggestions", []),
            scored=True,
        )
        return version, score_result, None

    run_result = router.complete("construct", [{"role": "user", "content": version.content}])
    output_text = run_result.text

    judgment = _judge_output(version.content, output_text, router)

    module_to_fix: str | None = judgment["weakest_module"]
    if module_to_fix is None and dimensions:
        candidate = _weakest_module(dimensions)
        if candidate in _VALID_MODULES:
            module_to_fix = candidate

    if module_to_fix is None:
        score_result = ScoreResult(
            composite=composite,
            dimensions=dimensions,
            suggestions=current_score_json.get("suggestions", []),
            scored=True,
        )
        return version, score_result, None

    modules = dict(version.modules_json or {})
    current_text = modules.get(module_to_fix, "")
    fix_instruction = judgment["fix_instruction"]

    rewrite_prompt = (
        f"Rewrite the following prompt module to improve it.\n"
        f"Module: {module_to_fix}\n"
        f"Current text:\n{current_text}\n\n"
        f"Instruction: {fix_instruction}\n\n"
        f"Return ONLY the rewritten module text, no explanation."
    )
    rewrite_result = router.complete("construct", [{"role": "user", "content": rewrite_prompt}])
    new_module_text = rewrite_result.text.strip()
    if not new_module_text:
        # LLM returned empty — return original version unchanged
        score_result = ScoreResult(
            composite=composite,
            dimensions=dimensions,
            suggestions=current_score_json.get("suggestions", []),
            scored=True,
        )
        return version, score_result, None

    new_version, score_result = edit_module(
        version_id=version_id,
        module_name=module_to_fix,
        new_text=new_module_text,
        router=router,
        db=db,
    )

    return new_version, score_result, module_to_fix
