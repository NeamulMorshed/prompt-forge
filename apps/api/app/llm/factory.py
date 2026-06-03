from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.mock_provider import MockProvider
from app.llm.providers.ollama_provider import OllamaProvider
from app.llm.router import LLMRouter


def build_router(
    groq_api_key: str = "",
    gemini_api_key: str = "",
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "mistral",
) -> LLMRouter:
    if groq_api_key:
        primary = GroqProvider(api_key=groq_api_key)
    else:
        primary = OllamaProvider(base_url=ollama_base_url, model=ollama_model)

    if gemini_api_key:
        fallback = GeminiProvider(api_key=gemini_api_key)
    elif groq_api_key:
        fallback = MockProvider()
    else:
        fallback = MockProvider()

    return LLMRouter(primary=primary, fallback=fallback)
