import json
from unittest.mock import MagicMock

from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter
from app.llm.types import CompletionResult
from app.pipeline.assembler import assemble
from app.pipeline.evaluator import ScoreResult, score


def _router_returning(json_text: str) -> LLMRouter:
    p = MagicMock()
    p.complete.return_value = CompletionResult(text=json_text, model="mock", prompt_tokens=50, completion_tokens=20)
    return LLMRouter(primary=p, fallback=MockProvider())


def _ctx():
    return assemble(
        session_slots={"goal": "get leads", "audience": "startup founders"},
        domain="marketing_content",
        intent="write a LinkedIn post",
        clarity=0.8,
        questions_asked=2,
        final_ccs=0.75,
    )


_GOOD_SCORES = json.dumps({
    "clarity": 8, "completeness": 8, "richness": 7,
    "actionability": 9, "goal_align": 8, "ai_perf": 8,
    "suggestions": ["Add a specific CTA", "Include a statistic"]
})

_BAD_SCORES = json.dumps({
    "clarity": 4, "completeness": 3, "richness": 5,
    "actionability": 4, "goal_align": 3, "ai_perf": 5,
    "suggestions": ["Clarify the goal", "Add target audience details"]
})


def test_score_returns_composite_0_to_100():
    result = score("some prompt", _ctx(), _router_returning(_GOOD_SCORES))
    assert 0 <= result.composite <= 100


def test_good_scores_give_high_composite():
    result = score("some prompt", _ctx(), _router_returning(_GOOD_SCORES))
    assert result.composite >= 70


def test_bad_scores_produce_gate_failures():
    result = score("some prompt", _ctx(), _router_returning(_BAD_SCORES))
    assert len(result.gate_failures) > 0
    assert "clarity" in result.gate_failures or "completeness" in result.gate_failures


def test_suggestions_returned():
    result = score("some prompt", _ctx(), _router_returning(_GOOD_SCORES))
    assert len(result.suggestions) >= 1


def test_score_falls_back_on_malformed_json():
    result = score("some prompt", _ctx(), _router_returning("not json"))
    assert isinstance(result, ScoreResult)
    assert result.composite == 50.0
