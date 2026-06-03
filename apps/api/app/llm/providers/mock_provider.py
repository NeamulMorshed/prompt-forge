from app.llm.providers.base import Provider
from app.llm.types import CompletionResult


def _count_tokens(text: str) -> int:
    # Crude deterministic token estimate (good enough for Phase 0 logging).
    return max(1, len(text.split()))


class MockProvider(Provider):
    def complete(self, model: str, messages: list[dict]) -> CompletionResult:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        text = f"[mock] response to: {last_user}"
        prompt_tokens = sum(_count_tokens(m["content"]) for m in messages)
        return CompletionResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=_count_tokens(text),
        )
