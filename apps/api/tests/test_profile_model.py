import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.models import ContextProfile, User
from app.profile.routes import _split_slots


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


def _user(db) -> User:
    u = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@test.com", password_hash="x", plan="free")
    db.add(u)
    db.commit()
    return u


def test_profile_created_with_defaults(db):
    user = _user(db)
    p = ContextProfile(user_id=user.id, name="My defaults", is_default=True, core_context={}, domain_overrides={})
    db.add(p)
    db.commit()
    db.refresh(p)
    assert p.is_default is True
    assert p.core_context == {}
    assert p.domain_overrides == {}


def test_upsert_does_not_create_duplicate(db):
    user = _user(db)
    # First insert
    p1 = ContextProfile(user_id=user.id, name="My defaults", is_default=True, core_context={"tone": "bold"}, domain_overrides={})
    db.add(p1)
    db.commit()
    # Update existing — must not add a second row
    p1.core_context = {"tone": "casual"}
    db.commit()
    count = db.query(ContextProfile).filter_by(user_id=user.id, is_default=True).count()
    assert count == 1


def test_split_slots_core_fields_separated():
    filled = {
        "tone": "bold",
        "audience": "founders",
        "channel": "LinkedIn",
        "goal": "get leads",
    }
    out = _split_slots(filled, "marketing_content")
    assert out.core_context == {"tone": "bold", "audience": "founders"}
    assert out.domain_overrides == {"marketing_content": {"channel": "LinkedIn", "goal": "get leads"}}


def test_split_slots_all_core():
    filled = {"tone": "bold", "audience": "x", "brand_name": "Acme", "constraints": "none"}
    out = _split_slots(filled, "marketing_content")
    assert out.core_context == filled
    assert out.domain_overrides == {}


def test_split_slots_empty():
    out = _split_slots({}, "marketing_content")
    assert out.core_context == {}
    assert out.domain_overrides == {}
