import json
from dataclasses import dataclass

from app.llm.router import LLMRouter

_KNOWN_DOMAINS = {"marketing_content", "writing_academic"}

_SYSTEM_PROMPT = (
    "You are a domain classifier for a prompt-generation tool. "
    "Given user input, identify the domain, the user's core intent, "
    "and how clear/specific the request is (0.0 = very vague, 1.0 = crystal clear). "
    f"Domains: {', '.join(sorted(_KNOWN_DOMAINS))}, general. "
    'Return JSON only, no extra text: {"domain": str, "intent": str, "clarity": float}'
)


@dataclass
class ClassifyResult:
    domain: str
    intent: str
    clarity: float


def classify(user_input: str, router: LLMRouter) -> ClassifyResult:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    result = router.complete("classify", messages)
    try:
        data = json.loads(result.text)
        return ClassifyResult(
            domain=str(data.get("domain", "general")),
            intent=str(data.get("intent", user_input[:100])),
            clarity=float(data.get("clarity", 0.5)),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return ClassifyResult(domain="general", intent=user_input[:100], clarity=0.5)
