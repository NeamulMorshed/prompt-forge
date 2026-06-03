import fakeredis
import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.db import models  # noqa: F401
from app.llm.types import CompletionResult
from app.main import app
from app.pipeline import routes as pipeline_routes
from app.pipeline.session import SessionStore


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    fake_store = SessionStore(redis_client=fake_redis)

    mock_router = MagicMock()

    def router_side_effect(stage, messages, user_plan="free"):
        responses = {
            "classify": '{"domain": "marketing_content", "intent": "write a post", "clarity": 0.8}',
            "phrase_q": '{"question": "What outcome do you want?", "chips": ["Leads", "Traffic"], "allow_freetext": true}',
            "evaluate": '{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":["Add CTA"]}',
            "construct": '{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":["Add CTA"]}',
        }
        return CompletionResult(
            text=responses.get(stage, "mock response"),
            model=f"mock/{stage}",
            prompt_tokens=10,
            completion_tokens=5,
        )

    mock_router.complete.side_effect = router_side_effect

    pipeline_routes._llm_router = mock_router
    pipeline_routes._session_store = fake_store

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_start_returns_session_id_and_question(client):
    resp = client.post("/generate/start", json={"input": "help me write a LinkedIn post about my SaaS"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] is not None
    assert body["status"] == "needs_question"
    assert body["question"] is not None
    assert "question" in body["question"]


def test_answer_returns_question_or_result(client):
    start = client.post("/generate/start", json={"input": "help me write a LinkedIn post"}).json()
    session_id = start["session_id"]
    slot_id = start["question"]["slot_id"]

    resp = client.post("/generate/answer", json={
        "session_id": session_id,
        "slot_id": slot_id,
        "answer": "Get beta signups",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("needs_question", "done")


def test_answer_missing_session_returns_404(client):
    resp = client.post("/generate/answer", json={
        "session_id": "nonexistent-session-id",
        "slot_id": "goal",
        "answer": "something",
    })
    assert resp.status_code == 404
