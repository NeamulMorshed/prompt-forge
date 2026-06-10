import uuid
import hashlib
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.api_keys.service import generate_key, revoke_key, list_keys, lookup_key, _hash_key


class TestHashKey:
    def test_produces_64_char_hex(self):
        result = _hash_key("pf_test_key_12345678")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        assert _hash_key("same") == _hash_key("same")

    def test_different_inputs_different_hash(self):
        assert _hash_key("key1") != _hash_key("key2")


class TestGenerateKey:
    def test_returns_raw_key_and_model(self):
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        user_id = uuid.uuid4()
        raw_key, api_key_model = generate_key(user_id=user_id, name="My Key", db=db)

        assert raw_key.startswith("pf_")
        assert len(raw_key) > 20
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_key_prefix_stored_correctly(self):
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        user_id = uuid.uuid4()
        raw_key, api_key_model = generate_key(user_id=user_id, name="Test", db=db)

        added_model = db.add.call_args[0][0]
        assert added_model.key_prefix == raw_key[:8]
        assert added_model.key_hash == _hash_key(raw_key)

    def test_raw_key_not_stored(self):
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        user_id = uuid.uuid4()
        raw_key, _ = generate_key(user_id=user_id, name="Test", db=db)

        added_model = db.add.call_args[0][0]
        assert raw_key not in str(added_model.__dict__)


class TestLookupKey:
    def test_returns_none_for_unknown_key(self):
        db = MagicMock()
        db.scalar.return_value = None
        result = lookup_key("unknown_key_123", db)
        assert result is None

    def test_returns_none_for_revoked_key(self):
        db = MagicMock()
        mock_key = MagicMock()
        mock_key.revoked = True
        db.scalar.return_value = mock_key
        result = lookup_key("revoked_key", db)
        assert result is None

    def test_returns_key_model_for_valid_key(self):
        db = MagicMock()
        mock_key = MagicMock()
        mock_key.revoked = False
        mock_key.user_id = uuid.uuid4()
        db.scalar.return_value = mock_key
        result = lookup_key("valid_key_123", db)
        assert result == mock_key


class TestRevokeKey:
    def test_revokes_owned_key(self):
        db = MagicMock()
        user_id = uuid.uuid4()
        mock_key = MagicMock()
        mock_key.user_id = user_id
        db.get.return_value = mock_key

        result = revoke_key(key_id=uuid.uuid4(), user_id=user_id, db=db)

        assert result is True
        assert mock_key.revoked is True
        db.commit.assert_called_once()

    def test_returns_false_for_wrong_owner(self):
        db = MagicMock()
        mock_key = MagicMock()
        mock_key.user_id = uuid.uuid4()  # different owner
        db.get.return_value = mock_key

        result = revoke_key(key_id=uuid.uuid4(), user_id=uuid.uuid4(), db=db)

        assert result is False

    def test_returns_false_for_missing_key(self):
        db = MagicMock()
        db.get.return_value = None

        result = revoke_key(key_id=uuid.uuid4(), user_id=uuid.uuid4(), db=db)

        assert result is False


class TestListKeys:
    def test_returns_non_revoked_keys_for_user(self):
        db = MagicMock()
        user_id = uuid.uuid4()
        mock_keys = [MagicMock(revoked=False), MagicMock(revoked=False)]
        db.scalars.return_value = mock_keys

        result = list_keys(user_id=user_id, db=db)

        assert result == mock_keys
        db.scalars.assert_called_once()

    def test_returns_empty_list_when_no_keys(self):
        db = MagicMock()
        db.scalars.return_value = []

        result = list_keys(user_id=uuid.uuid4(), db=db)

        assert result == []


from fastapi.testclient import TestClient
from app.main import app
from app.auth.deps import get_current_user
from app.db.base import get_db

client = TestClient(app)


def _mock_user():
    u = MagicMock()
    u.id = uuid.uuid4()
    u.plan = "pro"
    return u


class TestKeyRoutes:
    def test_create_key_returns_raw_key_once(self):
        user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: user

        with patch("app.api_keys.routes.generate_key") as mock_gen:
            mock_model = MagicMock()
            mock_model.id = uuid.uuid4()
            mock_model.name = "Test Key"
            mock_model.key_prefix = "pf_abc123"
            from datetime import datetime, timezone
            mock_model.created_at = datetime.now(timezone.utc)
            mock_gen.return_value = ("pf_abc123rawkey...", mock_model)

            resp = client.post("/v1/keys", json={"name": "Test Key"})

        app.dependency_overrides.clear()
        assert resp.status_code == 201
        data = resp.json()
        assert "key" in data
        assert data["key"].startswith("pf_")

    def test_list_keys_requires_auth(self):
        resp = client.get("/v1/keys")
        assert resp.status_code == 401

    def test_revoke_key_returns_ok(self):
        user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: user
        key_id = str(uuid.uuid4())

        with patch("app.api_keys.routes.revoke_key") as mock_rev:
            mock_rev.return_value = True
            resp = client.delete(f"/v1/keys/{key_id}")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
