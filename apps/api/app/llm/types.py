from dataclasses import dataclass


@dataclass
class CompletionResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
