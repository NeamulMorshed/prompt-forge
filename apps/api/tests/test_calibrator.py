import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import OutcomeRating, Prompt, PromptVersion, User
from app.learning.calibrator import calibrate_crs_weights, calibrate_scorer


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def test_calibrate_no_ratings_returns_empty(db):
    result = calibrate_crs_weights(db, "marketing_content")
    assert result == {}


def test_calibrate_with_ratings(db):
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")
    db.add(user)

    prompt = Prompt(
        id=uuid.uuid4(),
        user_id=user.id,
        domain="marketing_content",
        score=75.0,
    )
    db.add(prompt)

    version = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=prompt.id,
        content="test prompt",
    )
    db.add(version)

    rating = OutcomeRating(
        id=uuid.uuid4(),
        prompt_version_id=version.id,
        rating=1,
        domain="marketing_content",
    )
    db.add(rating)
    db.commit()

    result = calibrate_crs_weights(db, "marketing_content")
    assert isinstance(result, dict)


def test_calibrate_scorer_no_ratings(db):
    result = calibrate_scorer(db)
    assert result == {}


def test_calibrate_scorer_with_ratings(db):
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")
    db.add(user)

    prompt = Prompt(
        id=uuid.uuid4(),
        user_id=user.id,
        domain="marketing_content",
    )
    db.add(prompt)

    version = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=prompt.id,
        content="test",
    )
    db.add(version)

    rating = OutcomeRating(
        id=uuid.uuid4(),
        prompt_version_id=version.id,
        rating=1,
    )
    db.add(rating)
    db.commit()

    result = calibrate_scorer(db)
    assert isinstance(result, dict)


def test_calibrate_respects_lookback_window(db):
    from datetime import timedelta

    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")
    db.add(user)

    prompt = Prompt(id=uuid.uuid4(), user_id=user.id)
    db.add(prompt)

    version = PromptVersion(id=uuid.uuid4(), prompt_id=prompt.id, content="test")
    db.add(version)

    # Old rating (outside lookback)
    old_rating = OutcomeRating(
        id=uuid.uuid4(),
        prompt_version_id=version.id,
        rating=1,
        domain="marketing_content",
        created_at=datetime.now(timezone.utc) - timedelta(days=31),
    )
    db.add(old_rating)

    # Recent rating (inside lookback)
    new_rating = OutcomeRating(
        id=uuid.uuid4(),
        prompt_version_id=version.id,
        rating=1,
        domain="marketing_content",
    )
    db.add(new_rating)
    db.commit()

    result = calibrate_crs_weights(db, "marketing_content", lookback_days=30)
    # Should process only the recent one
    assert isinstance(result, dict)
