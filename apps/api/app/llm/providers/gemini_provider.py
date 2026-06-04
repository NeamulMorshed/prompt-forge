from google import genai
from google.genai import types

from app.llm.providers.base import Provider
from app.llm.types import CompletionResult


class GeminiProvider(Provider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def complete(self, model: str, messages: list[dict]) -> CompletionResult:
        system_parts: list[str] = []
        content_parts: list[str] = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role == "assistant":
                content_parts.append(f"[Assistant]: {content}")
            else:
                content_parts.append(content)

        combined = "\n\n".join(content_parts)
        config = None
        if system_parts:
            config = types.GenerateContentConfig(
                system_instruction="\n\n".join(system_parts)
            )

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=combined,
            config=config,
        )
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
