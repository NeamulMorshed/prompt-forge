import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.auth.api_key_deps import validate_api_key, _rate_limit_key


class TestRateLimitKey:
    def test_format(self):
        key_id = uuid.uuid4()
        result = _rate_limit_key(key_id, minute=42)
        assert str(key_id) in result
        assert "42" in result


class TestValidateApiKey:
    def test_raises_401_when_no_header(self):
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                validate_api_key(api_key=None, db=MagicMock())
            )
        assert exc_info.value.status_code == 401

    def test_raises_401_for_invalid_key(self):
        db = MagicMock()
        with patch("app.auth.api_key_deps.lookup_key") as mock_lookup:
            mock_lookup.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                import asyncio
                asyncio.get_event_loop().run_until_complete(
                    validate_api_key(api_key="bad_key", db=db)
                )
        assert exc_info.value.status_code == 401

    def test_returns_user_id_for_valid_key(self):
        db = MagicMock()
        mock_api_key = MagicMock()
        mock_api_key.user_id = uuid.uuid4()
        mock_api_key.id = uuid.uuid4()
        mock_api_key.rate_limit_per_minute = 60

        with patch("app.auth.api_key_deps.lookup_key") as mock_lookup, \
             patch("app.auth.api_key_deps._check_rate_limit") as mock_rl:
            mock_lookup.return_value = mock_api_key
            mock_rl.return_value = True
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                validate_api_key(api_key="pf_valid_key", db=db)
            )

        assert result == mock_api_key.user_id
