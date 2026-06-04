import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.models import AuditLog, User, Workspace
from app.audit.logger import log_event


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


def test_log_event_creates_record(db):
    user_id = uuid.uuid4()
    log_event(
        db=db,
        action="generate.start",
        user_id=user_id,
        resource_type="prompt",
        resource_id=str(uuid.uuid4()),
    )
    db.commit()
    log = db.query(AuditLog).first()
    assert log is not None
    assert log.action == "generate.start"
    assert log.user_id == user_id


def test_log_event_with_workspace(db):
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    log_event(
        db=db,
        action="workspace.invite",
        user_id=user_id,
        workspace_id=ws_id,
        resource_type="user",
        resource_id="invited@example.com",
        metadata={"role": "member"},
    )
    db.commit()
    log = db.query(AuditLog).filter_by(workspace_id=ws_id).first()
    assert log is not None
    assert log.extra_data["role"] == "member"


def test_log_event_does_not_raise_on_error(db, monkeypatch):
    def raise_error(*args, **kwargs):
        raise RuntimeError("DB unavailable")
    monkeypatch.setattr(db, "add", raise_error)
    log_event(db=db, action="test.action", user_id=uuid.uuid4())


# --- Audit query route ---

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.auth.deps import get_current_user
from app.db.base import get_db
from app.main import app


@pytest.fixture()
def audit_client():
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
    ws = Workspace(id=uuid.uuid4(), name="Test WS", seats=5)
    db.add(ws)
    user = User(id=uuid.uuid4(), email="owner@t.com", password_hash="x", workspace_id=ws.id)
    db.add(user)
    log = AuditLog(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=user.id,
        action="prompt.generate",
        resource_type="prompt",
        resource_id=str(uuid.uuid4()),
        extra_data=None,
    )
    db.add(log)
    db.commit()

    def override_auth():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_auth
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_get_audit_logs(audit_client):
    resp = audit_client.get("/audit")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "prompt.generate"


def test_audit_filter_by_action(audit_client):
    resp = audit_client.get("/audit?action=prompt.generate")
    assert resp.status_code == 200
    assert all(l["action"] == "prompt.generate" for l in resp.json())
