from app.llm.providers.mock_provider import MockProvider


def test_mock_provider_returns_deterministic_result():
    provider = MockProvider()
    messages = [{"role": "user", "content": "hello world"}]
    result = provider.complete("mock/model", messages)
    assert result.text.startswith("[mock]")
    assert result.model == "mock/model"
    assert result.prompt_tokens > 0
    assert result.completion_tokens > 0


def test_mock_provider_is_deterministic():
    provider = MockProvider()
    messages = [{"role": "user", "content": "same input"}]
    a = provider.complete("mock/model", messages)
    b = provider.complete("mock/model", messages)
    assert a == b
