import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.db.models import ApiKey


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_key(user_id: uuid.UUID, name: str, db: DBSession) -> tuple[str, ApiKey]:
    raw_key = f"pf_{secrets.token_urlsafe(32)}"
    api_key = ApiKey(
        user_id=user_id,
        name=name,
        key_hash=_hash_key(raw_key),
        key_prefix=raw_key[:8],
        rate_limit_per_minute=60,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return raw_key, api_key


def lookup_key(raw_key: str, db: DBSession) -> ApiKey | None:
    key_hash = _hash_key(raw_key)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if api_key is None or api_key.revoked:
        return None
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key


def revoke_key(key_id: uuid.UUID, user_id: uuid.UUID, db: DBSession) -> bool:
    api_key = db.get(ApiKey, key_id)
    if api_key is None or api_key.user_id != user_id:
        return False
    api_key.revoked = True
    db.commit()
    return True


def list_keys(user_id: uuid.UUID, db: DBSession) -> list[ApiKey]:
    return list(db.scalars(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.revoked.is_(False))
        .order_by(ApiKey.created_at.desc())
    ))
