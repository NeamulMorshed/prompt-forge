import json
import logging

from app.llm.router import LLMRouter

logger = logging.getLogger("app.ingestion.extractor")

_EXTRACT_SYSTEM = """You analyze web content to identify reusable structural patterns for prompt engineering.
Extract up to 3 abstract structural patterns from the content. Each pattern must describe STRUCTURE only — never copy the actual text.

Return a JSON array only, no extra text:
[
  {
    "structure": "short name like 'hook + body + cta'",
    "abstraction": "1-2 sentence description of the structural pattern, fully abstract",
    "confidence": 0.0-1.0
  }
]

Rules:
- NEVER include specific words, brand names, or copied text from the source
- If no clear structural pattern exists, return []
- Structure names must be in 3-8 words, lowercase, separated by ' + '"""


def extract_patterns(
    markdown: str,
    domain: str,
    source_url: str,
    router: LLMRouter,
) -> list[dict]:
    user_msg = f"Domain: {domain}\nSource: {source_url}\n\nContent:\n{markdown[:6000]}"
    messages = [
        {"role": "system", "content": _EXTRACT_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    result = router.complete("construct", messages)
    try:
        data = json.loads(result.text)
        if not isinstance(data, list):
            return []
        return [
            p for p in data
            if isinstance(p, dict)
            and "structure" in p
            and "abstraction" in p
            and len(p.get("abstraction", "")) > 20
        ]
    except json.JSONDecodeError:
        logger.warning("Failed to parse extraction response from %s", source_url)
        return []
