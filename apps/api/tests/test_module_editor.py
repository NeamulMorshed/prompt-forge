import pytest
import uuid
from unittest.mock import patch, MagicMock

from app.pipeline.constructor import build_modules
from app.pipeline.assembler import ContextObject, ContextValue


def _ctx(domain="marketing_content", slots=None) -> ContextObject:
    slots = slots or {
        "goal": "drive conversions",
        "audience": "small business owners",
        "channel": "email",
        "tone": "professional",
    }
    return ContextObject(
        domain=domain,
        intent="test",
        clarity=0.8,
        questions_asked=2,
        final_ccs=0.80,
        slots={k: ContextValue(value=v, source="session") for k, v in slots.items()},
    )


def test_build_modules_returns_dict():
    ctx = _ctx()
    modules = build_modules(ctx, model="gemini-2.0-flash")
    assert isinstance(modules, dict)


def test_build_modules_has_expected_keys():
    ctx = _ctx()
    modules = build_modules(ctx, model="gemini-2.0-flash")
    assert "role" in modules
    assert "objective" in modules
    assert "format" in modules
    assert "guardrails" in modules


def test_build_modules_values_are_strings():
    ctx = _ctx()
    modules = build_modules(ctx, model="gemini-2.0-flash")
    for key, val in modules.items():
        assert isinstance(val, str), f"Module {key!r} is not a string"


def test_modules_join_equals_construct_output():
    from app.pipeline.constructor import construct
    ctx = _ctx()
    modules = build_modules(ctx, model="gemini-2.0-flash")
    joined = "\n\n".join(v for v in modules.values() if v.strip())
    constructed = construct(ctx, model="gemini-2.0-flash")
    assert joined == constructed


# --- Orchestrator flush stores modules_json ---

def test_orchestrator_flush_stores_modules():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.base import Base
    from app.db.models import PromptVersion
    from app.pipeline.orchestrator import Orchestrator
    from app.pipeline.session import SessionStore
    from app.llm.types import CompletionResult

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    router = MagicMock()
    router.complete.return_value = MagicMock(
        text='{"domain":"marketing_content","intent":"test","clarity":0.8}',
        model="mock/gemini",
        prompt_tokens=5,
        completion_tokens=5,
    )
    store = SessionStore()
    orch = Orchestrator(router=router, store=store, db=db)

    with patch("app.pipeline.orchestrator.next_question", return_value=None), \
         patch("app.pipeline.orchestrator.build_modules", return_value={
             "role": "You are an expert.",
             "objective": "Goal: test",
             "guardrails": "State assumptions.",
             "context": "",
             "task": "",
             "format": "",
             "patterns": "",
             "examples": "",
             "reasoning": "",
         }) as mock_modules, \
         patch("app.pipeline.orchestrator.score") as mock_score:
        from app.pipeline.evaluator import ScoreResult
        mock_score.return_value = ScoreResult(composite=80.0, scored=True)
        turn = orch.start(initial_input="test ad", user_id=None)

    version = db.query(PromptVersion).first()
    assert version is not None
    assert version.modules_json is not None
    assert "role" in version.modules_json


# --- edit-module endpoint ---

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base, get_db
from app.db.models import Prompt, PromptVersion, User
from app.main import app


@pytest.fixture()
def edit_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    db = TestSession()
    user = User(id=uuid.uuid4(), email="e@e.com", password_hash="x")
    db.add(user)
    prompt = Prompt(id=uuid.uuid4(), user_id=user.id, domain="marketing_content", skills_applied=[], score=75.0)
    db.add(prompt)
    version = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=prompt.id,
        content="You are an expert.\n\nGoal: sell product.\n\nState assumptions.",
        score_json={"composite": 75.0, "dimensions": {}, "suggestions": []},
        modules_json={"role": "You are an expert.", "objective": "Goal: sell product.", "guardrails": "State assumptions."},
    )
    db.add(version)
    db.commit()
    client = TestClient(app)
    yield client, version
    app.dependency_overrides.clear()
    db.close()


def test_edit_module_returns_new_version(edit_client):
    client, version = edit_client
    with patch("app.pipeline.routes._llm_router") as mock_router:
        mock_router.complete.return_value = MagicMock(
            text='{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":9,"ai_perf":8,"suggestions":["good"]}',
            model="mock/gemini",
            prompt_tokens=5,
            completion_tokens=5,
        )
        resp = client.post("/generate/edit-module", json={
            "prompt_version_id": str(version.id),
            "module_name": "objective",
            "new_text": "Goal: drive 100 sales this quarter with urgency messaging.",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "new_prompt_version_id" in data
    assert "score" in data
    assert data["new_prompt_version_id"] != str(version.id)


def test_edit_module_rejects_unknown_module(edit_client):
    client, version = edit_client
    resp = client.post("/generate/edit-module", json={
        "prompt_version_id": str(version.id),
        "module_name": "nonexistent_module",
        "new_text": "something",
    })
    assert resp.status_code == 422
