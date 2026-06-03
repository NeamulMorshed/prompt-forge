from abc import ABC, abstractmethod

from app.llm.types import CompletionResult


class Provider(ABC):
    @abstractmethod
    def complete(self, model: str, messages: list[dict]) -> CompletionResult:
        """Return a completion for the given model and chat messages."""
        raise NotImplementedError
