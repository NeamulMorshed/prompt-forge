from unittest.mock import MagicMock, patch

from app.llm.providers.groq_provider import GroqProvider


def test_groq_provider_maps_sdk_response_to_result():
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(content="hi there"))]
    fake_completion.usage = MagicMock(prompt_tokens=5, completion_tokens=2)

    with patch("app.llm.providers.groq_provider.Groq") as groq_cls:
        groq_cls.return_value.chat.completions.create.return_value = fake_completion
        provider = GroqProvider(api_key="fake-key")
        result = provider.complete("groq/llama-3.1-8b-instant", [{"role": "user", "content": "hi"}])

    assert result.text == "hi there"
    assert result.model == "groq/llama-3.1-8b-instant"
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 2
