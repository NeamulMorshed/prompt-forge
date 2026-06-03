from groq import Groq

from app.llm.providers.base import Provider
from app.llm.types import CompletionResult


class GroqProvider(Provider):
    def __init__(self, api_key: str):
        self._client = Groq(api_key=api_key)

    def complete(self, model: str, messages: list[dict]) -> CompletionResult:
        # Strip the "groq/" routing prefix before calling the SDK.
        sdk_model = model.split("/", 1)[1] if "/" in model else model
        resp = self._client.chat.completions.create(model=sdk_model, messages=messages)
        return CompletionResult(
            text=resp.choices[0].message.content,
            model=model,
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
        )
