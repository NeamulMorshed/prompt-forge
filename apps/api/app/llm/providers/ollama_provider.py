import json
import urllib.request

from app.llm.providers.base import Provider
from app.llm.types import CompletionResult

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider(Provider):
    def __init__(self, base_url: str = _DEFAULT_BASE_URL, model: str = "mistral"):
        self._base_url = base_url.rstrip("/")
        self._default_model = model

    def complete(self, model: str, messages: list[dict]) -> CompletionResult:
        # Use default model — routing table may carry groq/gemini prefixes not valid for Ollama
        stripped = model.split("/", 1)[1] if "/" in model else model
        sdk_model = stripped if model.startswith("ollama/") else self._default_model
        payload = json.dumps({"model": sdk_model, "messages": messages, "stream": False}).encode()
        req = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        content = data["message"]["content"]
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        return CompletionResult(
            text=content,
            model=f"ollama/{sdk_model}",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
