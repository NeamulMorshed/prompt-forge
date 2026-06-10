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
