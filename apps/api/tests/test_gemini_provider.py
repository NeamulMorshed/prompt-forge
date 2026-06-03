from unittest.mock import MagicMock, patch

from app.llm.providers.gemini_provider import GeminiProvider


def test_gemini_provider_maps_response_to_result():
    mock_response = MagicMock()
    mock_response.text = "Generated content here"
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 12
    mock_usage.candidates_token_count = 8
    mock_response.usage_metadata = mock_usage

    with patch("app.llm.providers.gemini_provider.genai") as mock_genai:
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        provider = GeminiProvider(api_key="fake-key")
        result = provider.complete("gemini/gemini-2.0-flash", [{"role": "user", "content": "hello"}])

    assert result.text == "Generated content here"
    assert result.model == "gemini/gemini-2.0-flash"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 8


def test_gemini_provider_handles_missing_usage_metadata():
    mock_response = MagicMock()
    mock_response.text = "Some output"
    mock_response.usage_metadata = MagicMock(spec=[])  # no token count attrs

    with patch("app.llm.providers.gemini_provider.genai") as mock_genai:
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        provider = GeminiProvider(api_key="fake-key")
        result = provider.complete("gemini/gemini-2.0-flash", [{"role": "user", "content": "test"}])

    assert result.text == "Some output"
    assert result.prompt_tokens > 0
    assert result.completion_tokens > 0
