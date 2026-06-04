import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.deps import get_current_user
from app.db.base import Base, get_db
from app.db.models import User, Workspace, WorkspaceMember
from app.main import app


@pytest.fixture()
def ws_client():
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

    db = TestSession()
    user = User(id=uuid.uuid4(), email="owner@test.com", password_hash="x")
    db.add(user)
    db.commit()

    def override_auth():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_auth

    client = TestClient(app)
    yield client, user, TestSession
    app.dependency_overrides.clear()
    db.close()


def test_create_workspace(ws_client):
    client, user, Session = ws_client
    resp = client.post("/workspace", json={"name": "ACME Corp"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "ACME Corp"
    assert "id" in data


def test_get_my_workspace(ws_client):
    client, user, Session = ws_client
    client.post("/workspace", json={"name": "ACME Corp"})
    resp = client.get("/workspace/me")
    assert resp.status_code == 200
    assert resp.json()["name"] == "ACME Corp"


def test_list_workspace_members(ws_client):
    client, user, Session = ws_client
    client.post("/workspace", json={"name": "Test WS"})
    resp = client.get("/workspace/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


def test_invite_member_by_email(ws_client):
    client, user, Session = ws_client
    db = Session()
    client.post("/workspace", json={"name": "Test WS"})

    invited = User(id=uuid.uuid4(), email="member@test.com", password_hash="x")
    db.add(invited)
    db.commit()

    resp = client.post("/workspace/invite", json={"email": "member@test.com", "role": "member"})
    assert resp.status_code == 200

    resp2 = client.get("/workspace/members")
    emails = [m["email"] for m in resp2.json()]
    assert "member@test.com" in emails


def test_library_shows_workspace_prompts(ws_client):
    from app.db.models import Prompt, PromptVersion
    client, user, Session = ws_client
    db = Session()

    create_resp = client.post("/workspace", json={"name": "Shared WS"})
    ws_id = uuid.UUID(create_resp.json()["id"])

    shared_prompt_id = uuid.uuid4()
    shared_prompt = Prompt(
        id=shared_prompt_id,
        group_id=shared_prompt_id,
        user_id=user.id,
        workspace_id=ws_id,
        domain="marketing_content",
        skills_applied=[],
        score=80.0,
    )
    db.add(shared_prompt)
    db.flush()
    shared_version = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=shared_prompt_id,
        content="Test prompt content",
        score_json={"composite": 80.0, "dimensions": {}, "suggestions": []},
    )
    db.add(shared_version)
    db.commit()

    resp = client.get("/library?scope=workspace")
    assert resp.status_code == 200
    domains = [p["domain"] for p in resp.json()]
    assert "marketing_content" in domains
