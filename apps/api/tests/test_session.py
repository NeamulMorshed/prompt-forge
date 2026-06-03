import fakeredis
import pytest

from app.pipeline.session import SessionStore, SessionState


@pytest.fixture()
def store():
    fake = fakeredis.FakeRedis(decode_responses=True)
    return SessionStore(redis_client=fake)


def test_create_and_get_session(store):
    s = store.create(domain="marketing_content", initial_input="help me write a post", intent="write LinkedIn post", clarity=0.8)
    assert s.id is not None
    fetched = store.get(s.id)
    assert fetched is not None
    assert fetched.domain == "marketing_content"
    assert fetched.initial_input == "help me write a post"
    assert fetched.questions_asked == 0
    assert fetched.status == "active"


def test_update_session(store):
    s = store.create(domain="marketing_content", initial_input="x", intent="y", clarity=0.5)
    s.filled_slots["goal"] = "increase signups"
    s.questions_asked = 1
    store.update(s)
    fetched = store.get(s.id)
    assert fetched.filled_slots["goal"] == "increase signups"
    assert fetched.questions_asked == 1


def test_get_missing_session_returns_none(store):
    assert store.get("nonexistent-id") is None


def test_session_has_no_user_by_default(store):
    s = store.create(domain="marketing_content", initial_input="x", intent="y", clarity=0.5)
    assert s.user_id is None
