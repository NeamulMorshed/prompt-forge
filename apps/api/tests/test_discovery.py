import json
from unittest.mock import MagicMock

from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter
from app.llm.types import CompletionResult
from app.pipeline.crs_loader import Slot
from app.pipeline.discovery import Question, apply_answer, next_question

_SLOTS = [
    Slot(id="goal",     weight=0.20, required=True,  hint="What outcome do you want?"),
    Slot(id="audience", weight=0.18, required=True,  hint="Who is your audience?"),
    Slot(id="channel",  weight=0.15, required=True,  hint="What channel or format?"),
    Slot(id="tone",     weight=0.12, required=False, hint="What tone?"),
]


def _router_returning(json_text: str) -> LLMRouter:
    p = MagicMock()
    p.complete.return_value = CompletionResult(text=json_text, model="mock", prompt_tokens=5, completion_tokens=3)
    return LLMRouter(primary=p, fallback=MockProvider())


def test_next_question_returns_highest_weight_empty_slot():
    router = _router_returning(
        '{"question": "What outcome do you want?", "chips": ["Traffic", "Leads"], "allow_freetext": true}'
    )
    q = next_question(slots=_SLOTS, filled={}, history=[], questions_asked=0, router=router)
    assert q is not None
    assert q.slot_id == "goal"
    assert len(q.chips) >= 2


def test_next_question_skips_filled_slots():
    router = _router_returning(
        '{"question": "Who is your audience?", "chips": ["B2B", "B2C"], "allow_freetext": true}'
    )
    q = next_question(slots=_SLOTS, filled={"goal": "get leads"}, history=[], questions_asked=0, router=router)
    assert q is not None
    assert q.slot_id == "audience"


def test_next_question_returns_none_at_cap():
    router = _router_returning('{"question": "x", "chips": [], "allow_freetext": true}')
    q = next_question(slots=_SLOTS, filled={}, history=[], questions_asked=5, router=router)
    assert q is None


def test_next_question_returns_none_when_all_filled():
    filled = {"goal": "x", "audience": "x", "channel": "x", "tone": "x"}
    router = _router_returning('{"question": "x", "chips": [], "allow_freetext": true}')
    q = next_question(slots=_SLOTS, filled=filled, history=[], questions_asked=0, router=router)
    assert q is None


def test_next_question_falls_back_on_bad_llm_json():
    router = _router_returning("not json")
    q = next_question(slots=_SLOTS, filled={}, history=[], questions_asked=0, router=router)
    assert q is not None
    assert q.slot_id == "goal"
    assert q.question == _SLOTS[0].hint


def test_apply_answer_updates_dict():
    updated = apply_answer("goal", "Get newsletter signups", {})
    assert updated["goal"] == "Get newsletter signups"


def test_apply_answer_does_not_mutate_original():
    original = {"audience": "marketers"}
    updated = apply_answer("goal", "x", original)
    assert "goal" not in original
    assert updated["goal"] == "x"
