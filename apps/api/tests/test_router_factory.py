from app.llm.factory import build_router
from app.llm.providers.mock_provider import MockProvider
from app.llm.providers.ollama_provider import OllamaProvider


def test_build_router_uses_ollama_when_no_key():
    router = build_router(groq_api_key="")
    # No API keys → Ollama primary, Mock fallback.
    assert isinstance(router._primary, OllamaProvider)
    assert isinstance(router._fallback, MockProvider)


def test_build_router_uses_groq_when_key_present():
    router = build_router(groq_api_key="fake-key")
    assert type(router._primary).__name__ == "GroqProvider"
    assert isinstance(router._fallback, MockProvider)
