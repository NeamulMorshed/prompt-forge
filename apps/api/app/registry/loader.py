import json
from dataclasses import dataclass
from pathlib import Path

_PATTERNS_DIR = Path(__file__).parent.parent.parent.parent.parent / "packages" / "patterns"


@dataclass
class Pattern:
    """Abstracted prompt pattern for a domain."""

    id: str
    domain: str
    structure: str
    abstraction: str
    quality_score: float
    sources: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        return cls(
            id=data["id"],
            domain=data["domain"],
            structure=data["structure"],
            abstraction=data["abstraction"],
            quality_score=float(data["quality_score"]),
            sources=data.get("sources", []),
        )


def load_patterns(domain: str) -> list[Pattern]:
    """Load all patterns for a domain from JSONL file.

    Returns empty list if file doesn't exist.
    """
    path = _PATTERNS_DIR / f"{domain}.jsonl"
    if not path.exists():
        return []

    patterns = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                patterns.append(Pattern.from_dict(data))
    return patterns


def get_top_patterns(domain: str, limit: int = 5) -> list[Pattern]:
    """Retrieve top N patterns by quality score for a domain."""
    patterns = load_patterns(domain)
    return sorted(patterns, key=lambda p: p.quality_score, reverse=True)[:limit]
