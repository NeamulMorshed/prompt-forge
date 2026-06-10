import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.base import get_db
from app.db.models import User
from app.api_keys.service import generate_key, revoke_key, list_keys
from app.api_keys.schemas import (
    CreateKeyRequest, CreateKeyResponse,
    ListKeysResponse, KeySummary, RevokeKeyResponse,
)

router = APIRouter(prefix="/v1/keys", tags=["api-keys"])


@router.post("", response_model=CreateKeyResponse, status_code=status.HTTP_201_CREATED)
def create_key(
    body: CreateKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateKeyResponse:
    raw_key, api_key = generate_key(user_id=current_user.id, name=body.name, db=db)
    return CreateKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.get("", response_model=ListKeysResponse)
def list_user_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListKeysResponse:
    keys = list_keys(user_id=current_user.id, db=db)
    return ListKeysResponse(keys=[
        KeySummary(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            rate_limit_per_minute=k.rate_limit_per_minute,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ])


@router.delete("/{key_id}", response_model=RevokeKeyResponse)
def revoke_user_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RevokeKeyResponse:
    try:
        kid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid key ID")
    ok = revoke_key(key_id=kid, user_id=current_user.id, db=db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return RevokeKeyResponse(ok=True)
