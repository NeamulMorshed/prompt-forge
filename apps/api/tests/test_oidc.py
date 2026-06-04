import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base, get_db
from app.db.models import User, Workspace, OIDCConfig
from app.main import app


@pytest.fixture()
def oidc_client():
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
    db = TestSession()
    ws = Workspace(id=uuid.uuid4(), name="SSO Corp", seats=10)
    db.add(ws)
    config = OIDCConfig(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        discovery_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id="test-client-id",
        client_secret="test-secret",
    )
    db.add(config)
    db.commit()
    client = TestClient(app, follow_redirects=False)
    yield client, ws.id
    app.dependency_overrides.clear()


def test_oidc_login_redirects(oidc_client):
    client, ws_id = oidc_client
    with patch("app.auth.oidc.OAuth") as MockOAuth:
        mock_oauth_instance = MagicMock()
        mock_oidc_client = MagicMock()
        mock_oidc_client.authorize_redirect.return_value = MagicMock(
            status_code=302,
            headers={"location": "https://accounts.google.com/o/oauth2/auth?test=1"},
        )
        mock_oauth_instance.oidc = mock_oidc_client
        MockOAuth.return_value = mock_oauth_instance
        resp = client.get(f"/auth/oidc/login?workspace_id={ws_id}")
    assert resp.status_code in (302, 200, 307)


def test_oidc_config_save(oidc_client):
    client, ws_id = oidc_client
    from app.auth.deps import get_current_user
    owner = User(id=uuid.uuid4(), email="o@o.com", password_hash="x", workspace_id=ws_id)
    app.dependency_overrides[get_current_user] = lambda: owner

    resp = client.post("/auth/oidc/config", json={
        "discovery_url": "https://accounts.google.com/.well-known/openid-configuration",
        "client_id": "new-client",
        "client_secret": "new-secret",
    })
    assert resp.status_code in (200, 201, 409)
    app.dependency_overrides.pop(get_current_user, None)
