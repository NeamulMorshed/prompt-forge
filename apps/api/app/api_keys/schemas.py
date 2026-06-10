import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CreateKeyResponse(BaseModel):
    id: str
    name: str
    key: str           # raw key — shown ONCE, never again
    key_prefix: str
    created_at: datetime


class KeySummary(BaseModel):
    id: str
    name: str
    key_prefix: str
    rate_limit_per_minute: int
    created_at: datetime
    last_used_at: datetime | None = None


class ListKeysResponse(BaseModel):
    keys: list[KeySummary]


class RevokeKeyResponse(BaseModel):
    ok: bool
