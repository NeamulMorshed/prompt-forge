import uuid
from fastapi.testclient import TestClient

from app.db.models import Session as SessionModel
from app.db.base import get_db


def _make_token(client: TestClient) -> tuple[str, str]:
    """Signup and return (user_id_str, token)."""
    r = client.post("/auth/signup", json={"email": "profile@test.com", "password": "pw123456"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return r2.json()["id"], token


def test_get_profile_requires_auth(client):
    resp = client.get("/profile")
    assert resp.status_code == 401


def test_get_profile_returns_null_when_none(client):
    _, token = _make_token(client)
    resp = client.get("/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() is None


def test_put_profile_creates_profile(client):
    _, token = _make_token(client)
    body = {
        "core_context": {"tone": "bold", "audience": "founders"},
        "domain_overrides": {"marketing_content": {"channel": "LinkedIn"}},
    }
    resp = client.put("/profile", json=body, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["core_context"]["tone"] == "bold"
    assert data["domain_overrides"]["marketing_content"]["channel"] == "LinkedIn"


def test_put_profile_is_idempotent(client):
    _, token = _make_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/profile", json={"core_context": {"tone": "formal"}, "domain_overrides": {}}, headers=headers)
    resp2 = client.put("/profile", json={"core_context": {"tone": "casual"}, "domain_overrides": {}}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["core_context"]["tone"] == "casual"
    # Only one profile row should exist
    resp3 = client.get("/profile", headers=headers)
    assert resp3.json()["core_context"]["tone"] == "casual"


def test_put_profile_merges_partially(client):
    _, token = _make_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/profile", json={"core_context": {"tone": "bold", "audience": "founders"}, "domain_overrides": {}}, headers=headers)
    client.put("/profile", json={"core_context": {"audience": "designers"}, "domain_overrides": {}}, headers=headers)
    resp = client.get("/profile", headers=headers)
    data = resp.json()
    assert data["core_context"]["tone"] == "bold"       # preserved
    assert data["core_context"]["audience"] == "designers"  # updated


def test_delete_profile(client):
    _, token = _make_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/profile", json={"core_context": {"tone": "x"}, "domain_overrides": {}}, headers=headers)
    resp = client.delete("/profile", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    resp2 = client.get("/profile", headers=headers)
    assert resp2.json() is None


def test_extract_requires_auth(client):
    resp = client.post("/profile/extract", json={"session_id": "some-id"})
    assert resp.status_code == 401


def test_extract_returns_404_for_missing_session(client):
    _, token = _make_token(client)
    resp = client.post(
        "/profile/extract",
        json={"session_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_extract_splits_core_vs_domain(client):
    _, token = _make_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    # Inject a completed session directly into the DB
    db_gen = client.app.dependency_overrides[get_db]()
    db = next(db_gen)
    session_id = uuid.uuid4()
    db.add(SessionModel(
        id=session_id,
        domain="marketing_content",
        initial_input="x",
        filled_slots={"tone": "bold", "audience": "founders", "channel": "LinkedIn", "goal": "get leads"},
        questions_asked=2,
        ccs=0.8,
        status="complete",
    ))
    db.commit()

    resp = client.post(
        "/profile/extract",
        json={"session_id": str(session_id)},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["core_context"]["tone"] == "bold"
    assert data["core_context"]["audience"] == "founders"
    assert "channel" in data["domain_overrides"].get("marketing_content", {})
    assert "goal" in data["domain_overrides"].get("marketing_content", {})
    assert "channel" not in data["core_context"]


def test_extract_rejects_other_users_session(client):
    """User A cannot extract slots from User B's session."""
    # User A
    r = client.post("/auth/signup", json={"email": "usera@test.com", "password": "pw123456"})
    token_a = r.json()["access_token"]

    # User B
    r3 = client.post("/auth/signup", json={"email": "userb@test.com", "password": "pw123456"})
    token_b = r3.json()["access_token"]
    r4 = client.get("/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    user_b_id = uuid.UUID(r4.json()["id"])

    # Create a completed session belonging to User B
    db_gen = client.app.dependency_overrides[get_db]()
    db = next(db_gen)
    session_id = uuid.uuid4()
    db.add(SessionModel(
        id=session_id,
        user_id=user_b_id,
        domain="marketing_content",
        initial_input="x",
        filled_slots={"tone": "bold", "goal": "get leads"},
        questions_asked=1,
        ccs=0.8,
        status="complete",
    ))
    db.commit()

    # User A tries to extract — should get 404
    resp = client.post(
        "/profile/extract",
        json={"session_id": str(session_id)},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 404
