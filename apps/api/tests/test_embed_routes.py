import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.auth.api_key_deps import validate_api_key

_FAKE_USER_ID = uuid.uuid4()


class TestEmbedStart:
    def test_requires_api_key(self, client):
        resp = client.post("/v1/generate/start", json={"input": "write a blog post"})
        assert resp.status_code == 401

    def test_returns_session_id_and_status(self, client):
        app.dependency_overrides[validate_api_key] = lambda: _FAKE_USER_ID

        with patch("app.embed.routes._orch_for_user") as mock_orch:
            mock_turn = MagicMock()
            mock_turn.session_id = str(uuid.uuid4())
            mock_turn.status = "needs_question"
            mock_turn.question = MagicMock(
                slot_id="goal", question="What outcome?", chips=["awareness", "sales"], allow_freetext=True
            )
            mock_turn.result = None
            mock_orch.return_value.start.return_value = mock_turn

            resp = client.post(
                "/v1/generate/start",
                json={"input": "help me write content"},
                headers={"X-API-Key": "pf_fake"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["status"] == "needs_question"
        assert data["question"]["slot_id"] == "goal"

    def test_done_status_includes_prompt(self, client):
        app.dependency_overrides[validate_api_key] = lambda: _FAKE_USER_ID

        with patch("app.embed.routes._orch_for_user") as mock_orch:
            mock_turn = MagicMock()
            mock_turn.session_id = str(uuid.uuid4())
            mock_turn.status = "done"
            mock_turn.question = None
            mock_turn.result = MagicMock(
                prompt="You are an expert...",
                score=MagicMock(composite=82.5, suggestions=[]),
                prompt_version_id=str(uuid.uuid4()),
            )
            mock_orch.return_value.start.return_value = mock_turn

            resp = client.post(
                "/v1/generate/start",
                json={"input": "detailed specific request with full context"},
                headers={"X-API-Key": "pf_fake"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "done"
        assert data["result"]["prompt"] is not None


class TestEmbedAnswer:
    def test_answer_advances_session(self, client):
        app.dependency_overrides[validate_api_key] = lambda: _FAKE_USER_ID

        with patch("app.embed.routes._orch_for_user") as mock_orch:
            mock_turn = MagicMock()
            mock_turn.session_id = "sess_123"
            mock_turn.status = "done"
            mock_turn.question = None
            mock_turn.result = MagicMock(
                prompt="Generated prompt",
                score=MagicMock(composite=78.0, suggestions=[]),
                prompt_version_id=str(uuid.uuid4()),
            )
            mock_orch.return_value.answer.return_value = mock_turn

            resp = client.post(
                "/v1/generate/answer",
                json={"session_id": "sess_123", "slot_id": "goal", "answer": "brand awareness"},
                headers={"X-API-Key": "pf_fake"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_answer_404_for_unknown_session(self, client):
        app.dependency_overrides[validate_api_key] = lambda: _FAKE_USER_ID

        with patch("app.embed.routes._orch_for_user") as mock_orch:
            mock_orch.return_value.answer.side_effect = ValueError("Session not found")

            resp = client.post(
                "/v1/generate/answer",
                json={"session_id": "unknown", "slot_id": "goal", "answer": "test"},
                headers={"X-API-Key": "pf_fake"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 404
