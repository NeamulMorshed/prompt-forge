import json
import logging

from app.llm.providers.base import Provider
from app.llm.types import CompletionResult

logger = logging.getLogger("app.llm.router")

# Phase 0: single real provider (Groq). Gemini/Anthropic added in Phase 1.
ROUTING = {
    "classify": "groq/llama-3.1-8b-instant",
    "phrase_q": "groq/llama-3.1-8b-instant",
    "construct": "groq/llama-3.1-8b-instant",
    "evaluate": "groq/llama-3.1-8b-instant",
    "paid_construct": "groq/llama-3.1-8b-instant",
    "paid_evaluate": "groq/llama-3.1-8b-instant",
}

# Rough per-token cost estimate for logging (USD). Groq free tier is $0; placeholder for paid.
_COST_PER_1K_TOKENS = 0.0


class LLMRouter:
    def __init__(self, primary: Provider, fallback: Provider):
        self._primary = primary
        self._fallback = fallback

    def _model_for(self, stage: str, user_plan: str) -> str:
        key = f"paid_{stage}" if user_plan == "pro" and f"paid_{stage}" in ROUTING else stage
        return ROUTING.get(key, ROUTING["construct"])

    def complete(self, stage: str, messages: list[dict], user_plan: str = "free") -> CompletionResult:
        model = self._model_for(stage, user_plan)
        try:
            result = self._primary.complete(model, messages)
        except Exception as exc:  # noqa: BLE001 — failover is intentional
            logger.warning("primary provider failed (%s); falling back", exc)
            result = self._fallback.complete(model, messages)
        self._log_cost(stage, result)
        return result

    def _log_cost(self, stage: str, result: CompletionResult) -> None:
        total = result.prompt_tokens + result.completion_tokens
        est_cost = total / 1000 * _COST_PER_1K_TOKENS
        logger.info(
            json.dumps(
                {
                    "stage": stage,
                    "model": result.model,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "est_cost_usd": round(est_cost, 6),
                }
            )
        )
