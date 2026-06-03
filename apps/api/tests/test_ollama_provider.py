import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from app.llm.providers.ollama_provider import OllamaProvider


def _fake_response(content: str, prompt_tokens: int = 8, completion_tokens: int = 4):
    body = json.dumps({
        "message": {"role": "assistant", "content": content},
        "prompt_eval_count": prompt_tokens,
        "eval_count": completion_tokens,
    }).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_ollama_provider_returns_completion():
    with patch("urllib.request.urlopen", return_value=_fake_response("hello from ollama")):
        provider = OllamaProvider()
        result = provider.complete("ollama/mistral", [{"role": "user", "content": "hi"}])

    assert result.text == "hello from ollama"
    assert result.model == "ollama/mistral"
    assert result.prompt_tokens == 8
    assert result.completion_tokens == 4


def test_ollama_provider_strips_routing_prefix():
    with patch("urllib.request.urlopen", return_value=_fake_response("ok")):
        provider = OllamaProvider(model="llama2")
        result = provider.complete("ollama/llama2", [{"role": "user", "content": "x"}])

    assert result.model == "ollama/llama2"


def test_ollama_provider_uses_default_model_when_no_prefix():
    with patch("urllib.request.urlopen", return_value=_fake_response("ok")) as mock_open:
        provider = OllamaProvider(model="mistral")
        provider.complete("mistral", [{"role": "user", "content": "x"}])

    call_args = mock_open.call_args
    sent_payload = json.loads(call_args[0][0].data)
    assert sent_payload["model"] == "mistral"
