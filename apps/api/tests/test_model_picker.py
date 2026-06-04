import pytest
from unittest.mock import MagicMock, patch
from app.pipeline.schemas import StartRequest
from app.pipeline.orchestrator import Orchestrator
from app.pipeline.session import SessionStore
from app.llm.types import CompletionResult

_CLASSIFY_RESULT = '{"domain": "marketing_content", "intent": "test ad", "clarity": 0.8}'
_DISCOVERY_RESULT = '{"question": "Who is your audience?", "chips": ["B2B", "B2C"], "allow_freetext": true}'


def _mock_router(model_target: str = "gemini-2.0-flash"):
    router = MagicMock()
    router.complete.return_value = CompletionResult(
        text=_CLASSIFY_RESULT,
        model=f"mock/{model_target}",
        prompt_tokens=10,
        completion_tokens=10,
    )
    return router


def test_start_request_accepts_model_target():
    req = StartRequest(input="write me a Facebook ad", model_target="gpt-4o")
    assert req.model_target == "gpt-4o"


def test_start_request_model_target_defaults_none():
    req = StartRequest(input="write me a Facebook ad")
    assert req.model_target is None


def test_start_request_rejects_unknown_model():
    with pytest.raises(Exception):
        StartRequest(input="write me a Facebook ad", model_target="made-up-model-xyz")


def test_orchestrator_start_passes_model_target():
    router = _mock_router()
    store = SessionStore()
    orch = Orchestrator(router=router, store=store, db=None)
    with patch("app.pipeline.orchestrator.next_question", return_value=None), \
         patch("app.pipeline.orchestrator.construct", return_value="A prompt"), \
         patch("app.pipeline.orchestrator.score") as mock_score:
        from app.pipeline.evaluator import ScoreResult
        mock_score.return_value = ScoreResult(composite=80.0, scored=True)
        turn = orch.start(
            initial_input="write me a Facebook ad",
            user_id=None,
            model_target="gpt-4o",
        )
    assert turn is not None


# --- /run model_target routing test ---

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base, get_db
from app.db.models import Prompt, PromptVersion, User
from app.main import app
import uuid


@pytest.fixture()
def db_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    db = TestSession()
    yield client, db
    app.dependency_overrides.clear()
    db.close()


def test_run_uses_model_target(db_client):
    client, db = db_client
    user = User(id=uuid.uuid4(), email="t@t.com", password_hash="x")
    db.add(user)
    prompt = Prompt(
        id=uuid.uuid4(),
        user_id=user.id,
        domain="marketing_content",
        model_target="gpt-4o",
        skills_applied=[],
        score=80.0,
    )
    db.add(prompt)
    version = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=prompt.id,
        content="Write a great Facebook ad",
        score_json={},
    )
    db.add(version)
    db.commit()

    with patch("app.pipeline.routes._llm_router") as mock_router:
        mock_router.complete.return_value = CompletionResult(
            text="Great ad output",
            model="mock/gpt-4o",
            prompt_tokens=5,
            completion_tokens=5,
        )
        resp = client.post("/generate/run", json={"prompt_version_id": str(version.id)})
    assert resp.status_code == 200
    assert resp.json()["output"] == "Great ad output"
    called_stage = mock_router.complete.call_args[0][0]
    assert called_stage == "paid_construct"
