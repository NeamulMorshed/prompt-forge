from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter


def build_router(groq_api_key: str = "", gemini_api_key: str = "") -> LLMRouter:
    primary = GroqProvider(api_key=groq_api_key) if groq_api_key else MockProvider()
    fallback = GeminiProvider(api_key=gemini_api_key) if gemini_api_key else MockProvider()
    return LLMRouter(primary=primary, fallback=fallback)
