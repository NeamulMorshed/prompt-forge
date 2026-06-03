from app.llm.factory import build_router
from app.llm.providers.mock_provider import MockProvider


def test_build_router_uses_mock_when_no_key():
    router = build_router(groq_api_key="")
    # Both primary and fallback are mocks when no key is set.
    assert isinstance(router._primary, MockProvider)
    assert isinstance(router._fallback, MockProvider)


def test_build_router_uses_groq_when_key_present():
    router = build_router(groq_api_key="fake-key")
    assert type(router._primary).__name__ == "GroqProvider"
    assert isinstance(router._fallback, MockProvider)
