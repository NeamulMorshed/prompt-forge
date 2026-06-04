import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.base import get_db
from app.db.models import Prompt, PromptVersion, User


def _signup(client: TestClient, email: str) -> str:
    r = client.post("/auth/signup", json={"email": email, "password": "pw123456"})
    return r.json()["access_token"]


def _make_prompt(db, user_id: uuid.UUID, domain: str = "marketing_content") -> tuple[Prompt, PromptVersion]:
    p_id = uuid.uuid4()
    p = Prompt(
        id=p_id,
        user_id=user_id,
        domain=domain,
        group_id=p_id,
        score=75.0,
    )
    db.add(p)
    db.flush()
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=p_id,
        content="You are a marketing expert. Goal: get leads.",
        score_json={"composite": 75.0, "dimensions": {}, "suggestions": []},
    )
    db.add(v)
    db.commit()
    db.refresh(p)
    db.refresh(v)
    return p, v


def _get_db(client: TestClient):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def test_list_library_requires_auth(client):
    resp = client.get("/library")
    assert resp.status_code == 401


def test_list_library_returns_empty_for_new_user(client):
    token = _signup(client, "lib1@test.com")
    resp = client.get("/library", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_library_returns_user_prompts(client):
    token = _signup(client, "lib2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/auth/me", headers=headers)
    user_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    _make_prompt(db, user_id, "marketing_content")

    resp = client.get("/library", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["domain"] == "marketing_content"
    assert data[0]["version_count"] == 1
    assert "content_preview" in data[0]["latest_version"]


def test_list_library_filters_by_domain(client):
    token = _signup(client, "lib3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/auth/me", headers=headers)
    user_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    _make_prompt(db, user_id, "marketing_content")
    _make_prompt(db, user_id, "writing_academic")

    resp = client.get("/library?domain=marketing_content", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["domain"] == "marketing_content"


def test_list_library_does_not_return_other_users_prompts(client):
    token_a = _signup(client, "liba@test.com")
    token_b = _signup(client, "libb@test.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    user_a_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    _make_prompt(db, user_a_id)

    resp = client.get("/library", headers=headers_b)
    assert resp.json() == []


def test_get_prompt_group_returns_all_versions(client):
    token = _signup(client, "lib4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/auth/me", headers=headers)
    user_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    p, v = _make_prompt(db, user_id)

    resp = client.get(f"/library/{p.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_id"] == str(p.group_id)
    assert len(data["prompts"]) == 1
    assert len(data["prompts"][0]["versions"]) == 1
    assert data["prompts"][0]["versions"][0]["content"] == v.content


def test_get_prompt_group_returns_404_for_other_user(client):
    token_a = _signup(client, "lib5a@test.com")
    token_b = _signup(client, "lib5b@test.com")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    user_a_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    p, _ = _make_prompt(db, user_a_id)

    resp = client.get(f"/library/{p.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_patch_title(client):
    token = _signup(client, "lib6@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/auth/me", headers=headers)
    user_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    p, _ = _make_prompt(db, user_id)

    resp = client.patch(f"/library/{p.id}", json={"title": "My campaign"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    detail = client.get(f"/library/{p.id}", headers=headers).json()
    assert detail["prompts"][0]["title"] == "My campaign"


def test_patch_version_label(client):
    token = _signup(client, "lib7@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/auth/me", headers=headers)
    user_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    p, v = _make_prompt(db, user_id)

    resp = client.patch(
        f"/library/{p.id}/versions/{v.id}",
        json={"outcome_label": "worked great for IG"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    detail = client.get(f"/library/{p.id}", headers=headers).json()
    assert detail["prompts"][0]["versions"][0]["outcome_label"] == "worked great for IG"


def test_delete_prompt(client):
    token = _signup(client, "lib8@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/auth/me", headers=headers)
    user_id = uuid.UUID(r.json()["id"])

    db = _get_db(client)
    p, _ = _make_prompt(db, user_id)

    resp = client.delete(f"/library/{p.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp2 = client.get("/library", headers=headers)
    assert resp2.json() == []
