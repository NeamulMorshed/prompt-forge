import uuid
import fakeredis
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.db.base import get_db
from app.db.models import Prompt, PromptVersion
from app.db.models import Session as SessionModel
from app.llm.types import CompletionResult
from app.pipeline import routes as pipeline_routes
from app.pipeline.session import SessionStore


def _signup(client: TestClient, email: str) -> tuple[str, uuid.UUID]:
    r = client.post("/auth/signup", json={"email": email, "password": "pw123456"})
    token = r.json()["access_token"]
    r2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, uuid.UUID(r2.json()["id"])


def _get_db(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _make_complete_session(db, user_id: uuid.UUID) -> tuple[Prompt, PromptVersion]:
    sess_id = uuid.uuid4()
    db.add(SessionModel(
        id=sess_id,
        user_id=user_id,
        domain="marketing_content",
        initial_input="write a LinkedIn post",
        filled_slots={
            "goal": "get leads",
            "audience": "founders",
            "channel": "LinkedIn",
            "tone": "bold",         # adds 0.12 → total weight 0.65
            "constraints": "none",  # adds 0.10 → total weight 0.75 ≥ 0.70
        },
        questions_asked=2,
        ccs=0.85,
        status="complete",
    ))
    p_id = uuid.uuid4()
    p = Prompt(
        id=p_id,
        session_id=sess_id,
        user_id=user_id,
        domain="marketing_content",
        group_id=p_id,
        score=78.0,
    )
    db.add(p)
    db.flush()
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=p_id,
        content="You are a marketing expert. Goal: get leads.",
        score_json={"composite": 78.0, "dimensions": {}, "suggestions": []},
    )
    db.add(v)
    db.commit()
    db.refresh(p)
    db.refresh(v)
    return p, v


@pytest.fixture()
def client_with_mock_router(client):
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    fake_store = SessionStore(redis_client=fake_redis)

    mock_router = MagicMock()
    def router_side_effect(stage, messages, user_plan="free"):
        responses = {
            "classify": '{"domain": "marketing_content", "intent": "branch", "clarity": 0.9}',
            "phrase_q": '{"question": "x", "chips": [], "allow_freetext": true}',
            "evaluate": '{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":[]}',
            "construct": '{"clarity":8,"completeness":8,"richness":7,"actionability":8,"goal_align":8,"ai_perf":7,"suggestions":[]}',
        }
        return CompletionResult(
            text=responses.get(stage, "mock"),
            model=f"mock/{stage}",
            prompt_tokens=10,
            completion_tokens=5,
        )
    mock_router.complete.side_effect = router_side_effect

    pipeline_routes._llm_router = mock_router
    pipeline_routes._session_store = fake_store
    yield client


def test_branch_requires_auth(client):
    resp = client.post("/generate/branch", json={"prompt_version_id": str(uuid.uuid4())})
    assert resp.status_code == 401


def test_branch_returns_404_for_unknown_version(client_with_mock_router):
    token, _ = _signup(client_with_mock_router, "br1@test.com")
    resp = client_with_mock_router.post(
        "/generate/branch",
        json={"prompt_version_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_branch_returns_403_for_other_users_prompt(client_with_mock_router):
    token_a, user_a = _signup(client_with_mock_router, "bra@test.com")
    token_b, _ = _signup(client_with_mock_router, "brb@test.com")

    db = _get_db(client_with_mock_router)
    _, v = _make_complete_session(db, user_a)

    resp = client_with_mock_router.post(
        "/generate/branch",
        json={"prompt_version_id": str(v.id)},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


def test_branch_returns_turn_response(client_with_mock_router):
    token, user_id = _signup(client_with_mock_router, "br2@test.com")
    db = _get_db(client_with_mock_router)
    _, v = _make_complete_session(db, user_id)

    resp = client_with_mock_router.post(
        "/generate/branch",
        json={"prompt_version_id": str(v.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] is not None
    assert body["status"] in ("needs_question", "done")


def test_branch_new_prompt_inherits_group_id(client_with_mock_router):
    token, user_id = _signup(client_with_mock_router, "br3@test.com")
    db = _get_db(client_with_mock_router)
    original_prompt, v = _make_complete_session(db, user_id)
    original_group_id = original_prompt.group_id

    resp = client_with_mock_router.post(
        "/generate/branch",
        json={"prompt_version_id": str(v.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    turn = resp.json()
    assert turn["status"] == "done", f"Expected done, got {turn['status']}"

    new_version_id = uuid.UUID(turn["result"]["prompt_version_id"])
    new_version = db.get(PromptVersion, new_version_id)
    assert new_version is not None
    new_prompt = db.get(Prompt, new_version.prompt_id)
    assert new_prompt is not None
    assert new_prompt.group_id == original_group_id
    assert str(new_prompt.branched_from_version_id) == str(v.id)
