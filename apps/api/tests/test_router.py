import logging

from app.llm.providers.base import Provider
from app.llm.router import LLMRouter
from app.llm.types import CompletionResult


class _StubProvider(Provider):
    def __init__(self, text="ok"):
        self.calls = []
        self._text = text

    def complete(self, model, messages):
        self.calls.append(model)
        return CompletionResult(text=self._text, model=model, prompt_tokens=3, completion_tokens=1)


class _FailingProvider(Provider):
    def complete(self, model, messages):
        raise RuntimeError("rate limited")


def test_router_routes_stage_to_configured_model():
    primary = _StubProvider()
    router = LLMRouter(primary=primary, fallback=_StubProvider())
    router.complete("classify", [{"role": "user", "content": "hi"}])
    assert primary.calls == ["groq/llama-3.1-8b-instant"]


def test_router_unknown_stage_falls_back_to_construct_route():
    primary = _StubProvider()
    router = LLMRouter(primary=primary, fallback=_StubProvider())
    router.complete("does-not-exist", [{"role": "user", "content": "hi"}])
    assert primary.calls == ["groq/llama-3.1-8b-instant"]


def test_router_fails_over_to_fallback_on_error():
    fallback = _StubProvider(text="fallback")
    router = LLMRouter(primary=_FailingProvider(), fallback=fallback)
    result = router.complete("classify", [{"role": "user", "content": "hi"}])
    assert result.text == "fallback"
    assert fallback.calls == ["groq/llama-3.1-8b-instant"]


def test_router_logs_cost(caplog):
    router = LLMRouter(primary=_StubProvider(), fallback=_StubProvider())
    with caplog.at_level(logging.INFO, logger="app.llm.router"):
        router.complete("classify", [{"role": "user", "content": "hi"}])
    assert any("prompt_tokens" in r.message for r in caplog.records)
