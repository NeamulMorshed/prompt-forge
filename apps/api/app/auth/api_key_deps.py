import uuid
from datetime import datetime, timezone
from typing import Annotated

import redis as redis_lib
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session as DBSession

from app.api_keys.service import lookup_key
from app.db.base import get_db

try:
    from app.config import settings
    _redis = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    _redis = None


def _rate_limit_key(api_key_id: uuid.UUID, minute: int) -> str:
    return f"rl:apikey:{api_key_id}:{minute}"


def _check_rate_limit(api_key_id: uuid.UUID, limit: int) -> bool:
    if _redis is None:
        return True  # no Redis → skip rate limiting
    try:
        minute = int(datetime.now(timezone.utc).timestamp() // 60)
        rk = _rate_limit_key(api_key_id, minute)
        count = _redis.incr(rk)
        if count == 1:
            _redis.expire(rk, 120)  # 2-minute TTL
        return count <= limit
    except Exception:
        return True  # degrade gracefully on runtime Redis failure


async def validate_api_key(
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: DBSession = Depends(get_db),
) -> uuid.UUID:
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key header required")
    key_record = lookup_key(api_key, db)
    if key_record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")
    if not _check_rate_limit(key_record.id, key_record.rate_limit_per_minute):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    return key_record.user_id
