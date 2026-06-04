import uuid

import fakeredis
import pytest
from unittest.mock import MagicMock

from app.llm.providers.mock_provider import MockProvider
from app.llm.router import LLMRouter
from app.llm.types import CompletionResult
from app.pipeline.assembler import assemble
from app.pipeline.orchestrator import Orchestrator
from app.pipeline.session import SessionState, SessionStore


def _router() -> LLMRouter:
    p = MagicMock()
    def side_effect(stage, messages, user_plan="free"):
        responses = {
            "classify": '{"domain": "marketing_content", "intent": "write a post", "clarity": 0.8}',
            "phrase_q": '{"question": "What outcome?", "chips": ["Leads"], "allow_freetext": true}',
            "evaluate": '{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":[]}',
            "construct": '{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":[]}',
        }
        return CompletionResult(
            text=responses.get(stage, "{}"),
            model=f"mock/{stage}",
            prompt_tokens=10,
            completion_tokens=5,
        )
    p.complete.side_effect = side_effect
    return LLMRouter(primary=p, fallback=MockProvider())


@pytest.fixture()
def store():
    return SessionStore(redis_client=fakeredis.FakeRedis(decode_responses=True))


def test_load_profile_returns_merged_dict(store):
    valid_user_id = str(uuid.uuid4())
    mock_profile = MagicMock()
    mock_profile.core_context = {"tone": "bold", "audience": "founders"}
    mock_profile.domain_overrides = {"marketing_content": {"channel": "LinkedIn"}}
    mock_db = MagicMock()
    mock_db.scalar.return_value = mock_profile

    orch = Orchestrator(router=_router(), store=store, db=mock_db)
    result = orch._load_profile(valid_user_id, "marketing_content")

    assert result == {"tone": "bold", "audience": "founders", "channel": "LinkedIn"}


def test_load_profile_domain_override_wins_over_core(store):
    valid_user_id = str(uuid.uuid4())
    mock_profile = MagicMock()
    mock_profile.core_context = {"tone": "formal"}
    mock_profile.domain_overrides = {"marketing_content": {"tone": "edgy"}}
    mock_db = MagicMock()
    mock_db.scalar.return_value = mock_profile

    orch = Orchestrator(router=_router(), store=store, db=mock_db)
    result = orch._load_profile(valid_user_id, "marketing_content")
    assert result["tone"] == "edgy"


def test_load_profile_returns_empty_when_no_profile(store):
    valid_user_id = str(uuid.uuid4())
    mock_db = MagicMock()
    mock_db.scalar.return_value = None
    orch = Orchestrator(router=_router(), store=store, db=mock_db)
    assert orch._load_profile(valid_user_id, "marketing_content") == {}


def test_load_profile_returns_empty_when_db_none(store):
    orch = Orchestrator(router=_router(), store=store, db=None)
    assert orch._load_profile("user-123", "marketing_content") == {}


def test_profile_snapshot_stored_on_session(store):
    mock_profile = MagicMock()
    mock_profile.core_context = {"tone": "casual"}
    mock_profile.domain_overrides = {}
    mock_db = MagicMock()
    mock_db.scalar.return_value = mock_profile

    orch = Orchestrator(router=_router(), store=store, db=mock_db)
    result = orch.start(initial_input="write a post", user_id=str(uuid.uuid4()))
    session = store.get(result.session_id)
    assert session.profile_snapshot == {"tone": "casual"}


def test_ignore_profile_skips_load(store):
    mock_db = MagicMock()
    orch = Orchestrator(router=_router(), store=store, db=mock_db)
    result = orch.start(initial_input="write a post", user_id=str(uuid.uuid4()), ignore_profile=True)
    session = store.get(result.session_id)
    assert session.profile_snapshot == {}
    mock_db.scalar.assert_not_called()


def test_session_slot_overrides_profile_in_assembler():
    ctx = assemble(
        session_slots={"tone": "casual"},
        domain="marketing_content",
        intent="write a post",
        clarity=0.8,
        questions_asked=1,
        final_ccs=0.75,
        profile={"tone": "formal"},
        domain_defaults={},
    )
    assert ctx.slots["tone"].value == "casual"
    assert ctx.slots["tone"].source == "session"


def test_suggest_profile_save_true_when_no_profile(store):
    mock_db = MagicMock()
    mock_db.scalar.return_value = None
    mock_db.merge = MagicMock()
    mock_db.add = MagicMock()
    mock_db.flush = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.get = MagicMock(return_value=None)

    orch = Orchestrator(router=_router(), store=store, db=mock_db)

    session = SessionState(
        id=str(uuid.uuid4()),
        domain="marketing_content",
        initial_input="x",
        intent="write a LinkedIn post",
        clarity=0.8,
        user_id="user-123",
        filled_slots={"goal": "get leads", "audience": "founders", "channel": "LinkedIn"},
        profile_snapshot={},
    )
    store.update(session)
    result = orch._generate(session)
    assert result.suggest_profile_save is True
    assert "goal" in result.extractable_slots


def test_suggest_profile_save_false_when_profile_loaded(store):
    mock_db = MagicMock()
    mock_db.scalar.return_value = None
    mock_db.merge = MagicMock()
    mock_db.add = MagicMock()
    mock_db.flush = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.get = MagicMock(return_value=None)

    orch = Orchestrator(router=_router(), store=store, db=mock_db)

    session = SessionState(
        id=str(uuid.uuid4()),
        domain="marketing_content",
        initial_input="x",
        intent="y",
        clarity=0.8,
        user_id="user-123",
        filled_slots={"goal": "x", "audience": "y", "channel": "z"},
        profile_snapshot={"tone": "bold"},
    )
    store.update(session)
    result = orch._generate(session)
    assert result.suggest_profile_save is False


def test_suggest_profile_save_false_for_anon(store):
    mock_db = MagicMock()
    mock_db.scalar.return_value = None
    mock_db.merge = MagicMock()
    mock_db.add = MagicMock()
    mock_db.flush = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.get = MagicMock(return_value=None)

    orch = Orchestrator(router=_router(), store=store, db=mock_db)

    session = SessionState(
        id=str(uuid.uuid4()),
        domain="marketing_content",
        initial_input="x",
        intent="y",
        clarity=0.8,
        user_id=None,
        filled_slots={"goal": "x", "audience": "y", "channel": "z"},
        profile_snapshot={},
    )
    store.update(session)
    result = orch._generate(session)
    assert result.suggest_profile_save is False
