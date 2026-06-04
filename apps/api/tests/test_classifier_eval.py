"""
Classifier eval set — regression tests against ground-truth domain labels.

Two modes:
  1. Mock mode (default, runs in CI): verifies parser + fallback logic deterministically.
  2. Live mode (requires GROQ_API_KEY env var): runs all 60 cases against real LLM,
     asserts accuracy ≥ ACCURACY_THRESHOLD. Run manually before shipping classifier changes.

     pytest tests/test_classifier_eval.py -m live -v
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter
from app.llm.types import CompletionResult
from app.pipeline.classifier import ClassifyResult, classify

_CASES_PATH = (
    Path(__file__).parent.parent.parent.parent / "packages" / "eval" / "classifier_cases.json"
)
_ACCURACY_THRESHOLD = 0.90  # ≥90% correct domain on live run


def _load_cases() -> list[dict]:
    return json.loads(_CASES_PATH.read_text())["cases"]


def _router_returning(domain: str, intent: str = "test", clarity: float = 0.8) -> LLMRouter:
    p = MagicMock()
    p.complete.return_value = CompletionResult(
        text=json.dumps({"domain": domain, "intent": intent, "clarity": clarity}),
        model="mock",
        prompt_tokens=10,
        completion_tokens=5,
    )
    return LLMRouter(primary=p, fallback=MockProvider())


# ---------------------------------------------------------------------------
# Dataset integrity
# ---------------------------------------------------------------------------

def test_eval_dataset_loads():
    cases = _load_cases()
    assert len(cases) >= 50, f"Expected ≥50 cases, got {len(cases)}"


def test_eval_dataset_has_required_fields():
    for c in _load_cases():
        assert "id" in c
        assert "input" in c and c["input"].strip()
        assert "expected_domain" in c
        assert c["expected_domain"] in ("marketing_content", "writing_academic", "general")


def test_eval_dataset_domain_distribution():
    cases = _load_cases()
    by_domain: dict[str, int] = {}
    for c in cases:
        by_domain[c["expected_domain"]] = by_domain.get(c["expected_domain"], 0) + 1
    assert by_domain.get("marketing_content", 0) >= 20
    assert by_domain.get("writing_academic", 0) >= 20
    assert by_domain.get("general", 0) >= 5


def test_eval_dataset_ids_are_unique():
    cases = _load_cases()
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "Duplicate IDs found"


# ---------------------------------------------------------------------------
# Mock-mode: parser + fallback correctness (deterministic, runs in CI)
# ---------------------------------------------------------------------------

def test_classify_returns_marketing_domain():
    router = _router_returning("marketing_content")
    result = classify("Write a LinkedIn post", router)
    assert result.domain == "marketing_content"
    assert isinstance(result, ClassifyResult)


def test_classify_returns_academic_domain():
    router = _router_returning("writing_academic")
    result = classify("Help with my PhD thesis", router)
    assert result.domain == "writing_academic"


def test_classify_returns_general_domain():
    router = _router_returning("general")
    result = classify("Write a poem", router)
    assert result.domain == "general"


def test_classify_clarity_in_valid_range():
    for clarity in [0.0, 0.5, 1.0]:
        router = _router_returning("marketing_content", clarity=clarity)
        result = classify("test", router)
        assert 0.0 <= result.clarity <= 1.0


def test_classify_truncates_intent_on_fallback():
    p = MagicMock()
    p.complete.return_value = CompletionResult(
        text="not valid json {{{}",
        model="mock",
        prompt_tokens=5,
        completion_tokens=2,
    )
    router = LLMRouter(primary=p, fallback=MockProvider())
    long_input = "x" * 200
    result = classify(long_input, router)
    assert result.domain == "general"
    assert len(result.intent) <= 100


def test_classify_fallback_on_missing_domain_key():
    p = MagicMock()
    p.complete.return_value = CompletionResult(
        text=json.dumps({"intent": "something", "clarity": 0.7}),
        model="mock",
        prompt_tokens=5,
        completion_tokens=2,
    )
    router = LLMRouter(primary=p, fallback=MockProvider())
    result = classify("some input", router)
    assert result.domain == "general"


def test_classify_fallback_on_wrong_types():
    p = MagicMock()
    p.complete.return_value = CompletionResult(
        text=json.dumps({"domain": 123, "intent": None, "clarity": "high"}),
        model="mock",
        prompt_tokens=5,
        completion_tokens=2,
    )
    router = LLMRouter(primary=p, fallback=MockProvider())
    # Should not raise — coerces types or falls back
    result = classify("some input", router)
    assert isinstance(result, ClassifyResult)
    assert isinstance(result.clarity, float)


def test_classify_handles_empty_string():
    router = _router_returning("general", clarity=0.1)
    result = classify("", router)
    assert isinstance(result, ClassifyResult)


def test_classify_handles_extra_llm_fields():
    # LLM returns extra keys — should not break parsing
    p = MagicMock()
    p.complete.return_value = CompletionResult(
        text=json.dumps({
            "domain": "marketing_content",
            "intent": "write post",
            "clarity": 0.9,
            "extra_field": "ignored",
            "confidence": 0.95,
        }),
        model="mock",
        prompt_tokens=10,
        completion_tokens=5,
    )
    router = LLMRouter(primary=p, fallback=MockProvider())
    result = classify("Write a LinkedIn post", router)
    assert result.domain == "marketing_content"
    assert result.clarity == 0.9


@pytest.mark.parametrize("domain", ["marketing_content", "writing_academic", "general"])
def test_classify_all_known_domains_parse_correctly(domain: str):
    router = _router_returning(domain)
    result = classify("test input", router)
    assert result.domain == domain


# ---------------------------------------------------------------------------
# Live mode — real LLM accuracy gate (skip unless GROQ_API_KEY set)
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
def test_classifier_accuracy_live():
    from app.llm.factory import build_router

    router = build_router(groq_api_key=os.environ["GROQ_API_KEY"])
    cases = _load_cases()
    correct = 0
    failures: list[dict] = []

    for c in cases:
        result = classify(c["input"], router)
        if result.domain == c["expected_domain"]:
            correct += 1
        else:
            failures.append({
                "id": c["id"],
                "input": c["input"][:60],
                "expected": c["expected_domain"],
                "got": result.domain,
                "clarity": result.clarity,
            })

    total = len(cases)
    accuracy = correct / total
    failure_report = "\n".join(
        f"  {f['id']}: expected={f['expected']} got={f['got']} | {f['input']!r}"
        for f in failures
    )
    assert accuracy >= _ACCURACY_THRESHOLD, (
        f"Classifier accuracy {accuracy:.1%} below threshold {_ACCURACY_THRESHOLD:.1%} "
        f"({correct}/{total} correct)\nFailures:\n{failure_report}"
    )
