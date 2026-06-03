import fakeredis
import pytest
from unittest.mock import MagicMock

from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter
from app.llm.types import CompletionResult
from app.pipeline.orchestrator import Orchestrator, TurnResult
from app.pipeline.session import SessionStore


def _mock_router(classify_json: str, phrase_json: str, eval_json: str) -> LLMRouter:
    responses = {
        "classify": classify_json,
        "phrase_q": phrase_json,
        "evaluate": eval_json,
        "construct": eval_json,
    }

    router = LLMRouter(primary=MockProvider(), fallback=MockProvider())

    def complete(stage: str, messages: list, user_plan: str = "free") -> CompletionResult:
        return CompletionResult(
            text=responses.get(stage, "{}"),
            model=f"mock/{stage}",
            prompt_tokens=10,
            completion_tokens=5,
        )

    router.complete = complete  # type: ignore[method-assign]
    return router


@pytest.fixture()
def store():
    return SessionStore(redis_client=fakeredis.FakeRedis(decode_responses=True))


def test_start_returns_question_when_discovery_needed(store):
    router = _mock_router(
        classify_json='{"domain": "marketing_content", "intent": "write a post", "clarity": 0.5}',
        phrase_json='{"question": "What outcome do you want?", "chips": ["Leads", "Traffic"], "allow_freetext": true}',
        eval_json='{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":[]}',
    )
    orch = Orchestrator(router=router, store=store)
    result = orch.start(initial_input="help me write a LinkedIn post", user_id=None)
    assert result.status == "needs_question"
    assert result.question is not None
    assert result.session_id is not None
    assert result.result is None


def test_answer_increments_question_count(store):
    router = _mock_router(
        classify_json='{"domain": "marketing_content", "intent": "write a post", "clarity": 0.5}',
        phrase_json='{"question": "Who is your audience?", "chips": ["B2B"], "allow_freetext": true}',
        eval_json='{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":[]}',
    )
    orch = Orchestrator(router=router, store=store)
    start = orch.start(initial_input="help me write a LinkedIn post", user_id=None)
    session_id = start.session_id
    slot_id = start.question.slot_id

    result = orch.answer(session_id=session_id, slot_id=slot_id, answer="Get beta signups")
    session = store.get(session_id)
    assert session.questions_asked == 1
    assert session.filled_slots.get(slot_id) == "Get beta signups"


def test_start_session_is_stored(store):
    router = _mock_router(
        classify_json='{"domain": "marketing_content", "intent": "x", "clarity": 0.5}',
        phrase_json='{"question": "x", "chips": [], "allow_freetext": true}',
        eval_json='{}',
    )
    orch = Orchestrator(router=router, store=store)
    result = orch.start(initial_input="test", user_id=None)
    session = store.get(result.session_id)
    assert session is not None
    assert session.domain == "marketing_content"


def test_answer_with_invalid_session_raises(store):
    router = _mock_router('{}', '{}', '{}')
    orch = Orchestrator(router=router, store=store)
    with pytest.raises(ValueError):
        orch.answer(session_id="nonexistent", slot_id="goal", answer="x")
