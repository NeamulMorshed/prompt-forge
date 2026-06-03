from unittest.mock import MagicMock

from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter
from app.llm.types import CompletionResult
from app.pipeline.classifier import ClassifyResult, classify


def _router_with_response(json_text: str) -> LLMRouter:
    provider = MagicMock()
    provider.complete.return_value = CompletionResult(
        text=json_text, model="mock", prompt_tokens=10, completion_tokens=5
    )
    return LLMRouter(primary=provider, fallback=MockProvider())


def test_classify_returns_valid_domain():
    router = _router_with_response(
        '{"domain": "marketing_content", "intent": "write a LinkedIn post", "clarity": 0.8}'
    )
    result = classify("Write a LinkedIn post about our product launch", router)
    assert result.domain == "marketing_content"
    assert 0.0 <= result.clarity <= 1.0
    assert isinstance(result.intent, str)


def test_classify_falls_back_on_malformed_json():
    router = _router_with_response("this is not json at all")
    result = classify("some input", router)
    assert result.domain == "general"
    assert result.clarity == 0.5


def test_classify_result_is_dataclass():
    router = _router_with_response(
        '{"domain": "writing_academic", "intent": "write a thesis intro", "clarity": 0.9}'
    )
    result = classify("Help with my thesis introduction", router)
    assert isinstance(result, ClassifyResult)
    assert result.domain == "writing_academic"
