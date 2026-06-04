import json
import logging

from app.llm.providers.base import Provider
from app.llm.types import CompletionResult

logger = logging.getLogger("app.llm.router")

ROUTING = {
    "classify":        "groq/llama-3.1-8b-instant",
    "phrase_q":        "groq/llama-3.1-8b-instant",
    "construct":       "gemini/gemini-2.0-flash",
    "evaluate":        "gemini/gemini-2.0-flash",
    "paid_construct":  "anthropic/claude-sonnet-4-6",
    "paid_evaluate":   "anthropic/claude-sonnet-4-6",
    "gpt4o_construct": "openai/gpt-4o",
}

_COST_PER_1K_TOKENS: dict[str, float] = {
    "groq":      0.0,
    "gemini":    0.0,
    "anthropic": 0.003,
    "openai":    0.005,
    "ollama":    0.0,
    "mock":      0.0,
}


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
        except Exception as exc:  # noqa: BLE001
            logger.warning("primary provider failed (%s); falling back", exc)
            result = self._fallback.complete(model, messages)
        self._log_cost(stage, result)
        return result

    def _log_cost(self, stage: str, result: CompletionResult) -> None:
        provider_prefix = result.model.split("/")[0] if "/" in result.model else "mock"
        rate = _COST_PER_1K_TOKENS.get(provider_prefix, 0.0)
        total = result.prompt_tokens + result.completion_tokens
        est_cost = total / 1000 * rate
        logger.info(
            json.dumps({
                "stage": stage,
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "est_cost_usd": round(est_cost, 6),
            })
        )
