import google.generativeai as genai

from app.llm.providers.base import Provider
from app.llm.types import CompletionResult


class GeminiProvider(Provider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    def complete(self, model: str, messages: list[dict]) -> CompletionResult:
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"[System instructions]: {content}")
            elif role == "assistant":
                parts.append(f"[Assistant]: {content}")
            else:
                parts.append(content)
        combined = "\n\n".join(parts)

        response = self._model.generate_content(combined)
        text = response.text

        try:
            prompt_tokens = response.usage_metadata.prompt_token_count
            completion_tokens = response.usage_metadata.candidates_token_count
        except AttributeError:
            prompt_tokens = max(1, len(combined.split()))
            completion_tokens = max(1, len(text.split()))

        return CompletionResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
