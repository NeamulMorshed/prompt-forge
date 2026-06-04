import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.models import Prompt, User


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


def _prompt(db, user_id: uuid.UUID, group_id: uuid.UUID | None = None) -> Prompt:
    pid = uuid.uuid4()
    p = Prompt(
        id=pid,
        user_id=user_id,
        domain="marketing_content",
        score=80.0,
        group_id=group_id or pid,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_prompt_group_id_defaults_to_own_id(db):
    user = _user(db)
    p = _prompt(db, user.id)
    assert p.group_id == p.id


def test_branch_inherits_parent_group_id(db):
    user = _user(db)
    root = _prompt(db, user.id)

    branch = _prompt(db, user.id, group_id=root.group_id)
    assert branch.group_id == root.group_id
    assert branch.group_id == root.id


def test_branch_of_branch_still_has_root_group_id(db):
    user = _user(db)
    root = _prompt(db, user.id)
    branch1 = _prompt(db, user.id, group_id=root.group_id)
    branch2 = _prompt(db, user.id, group_id=root.group_id)

    assert branch2.group_id == root.id
    assert branch1.group_id == root.id


def test_prompt_has_created_at(db):
    user = _user(db)
    p = _prompt(db, user.id)
    assert p.created_at is not None


def test_prompt_title_nullable(db):
    user = _user(db)
    p = _prompt(db, user.id)
    assert p.title is None
    p.title = "My best prompt"
    db.commit()
    db.refresh(p)
    assert p.title == "My best prompt"
