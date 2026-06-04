import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.base import get_db
from app.db.models import ContextProfile
from app.db.models import Session as SessionModel
from app.db.models import User
from app.profile.schemas import ExtractOut, ExtractRequest, ProfileOut, ProfileUpsert

router = APIRouter(prefix="/profile", tags=["profile"])

_CORE_FIELDS = {"tone", "audience", "brand_name", "constraints"}


def _get_default(user_id: uuid.UUID, db: Session) -> ContextProfile | None:
    return db.scalar(
        select(ContextProfile).where(
            ContextProfile.user_id == user_id,
            ContextProfile.is_default.is_(True),
        )
    )


def _split_slots(filled: dict[str, str], domain: str) -> ExtractOut:
    core = {k: v for k, v in filled.items() if k in _CORE_FIELDS}
    domain_slots = {k: v for k, v in filled.items() if k not in _CORE_FIELDS}
    return ExtractOut(
        core_context=core,
        domain_overrides={domain: domain_slots} if domain_slots else {},
    )


@router.get("", response_model=ProfileOut | None)
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContextProfile | None:
    return _get_default(user.id, db)


@router.put("", response_model=ProfileOut)
def upsert_profile(
    body: ProfileUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContextProfile:
    profile = _get_default(user.id, db)
    if profile is None:
        profile = ContextProfile(
            user_id=user.id,
            name="My defaults",
            is_default=True,
            core_context=body.core_context,
            domain_overrides=body.domain_overrides,
        )
        db.add(profile)
    else:
        merged_core = {**profile.core_context, **body.core_context}
        merged_overrides = dict(profile.domain_overrides)
        for domain, slots in body.domain_overrides.items():
            merged_overrides[domain] = {**merged_overrides.get(domain, {}), **slots}
        profile.core_context = merged_core
        profile.domain_overrides = merged_overrides
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("", response_model=dict)
def delete_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    profile = _get_default(user.id, db)
    if profile:
        db.delete(profile)
        db.commit()
    return {"ok": True}


@router.post("/extract", response_model=ExtractOut)
def extract_profile(
    body: ExtractRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExtractOut:
    try:
        session_id = uuid.UUID(body.session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    db_session = db.get(SessionModel, session_id)
    if db_session is None or db_session.status != "complete":
        raise HTTPException(status_code=404, detail="Session not found or not complete")
    return _split_slots(db_session.filled_slots or {}, db_session.domain or "general")
