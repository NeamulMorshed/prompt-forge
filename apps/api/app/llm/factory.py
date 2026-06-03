from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter


def build_router(groq_api_key: str) -> LLMRouter:
    fallback = MockProvider()
    primary = GroqProvider(api_key=groq_api_key) if groq_api_key else MockProvider()
    return LLMRouter(primary=primary, fallback=fallback)
