import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.base import get_db
from app.db.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogOut(BaseModel):
    id: str
    action: str
    user_id: str | None
    resource_type: str | None
    resource_id: str | None
    metadata: dict | None
    created_at: datetime


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    action: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLogOut]:
    if not current_user.workspace_id:
        raise HTTPException(status_code=403, detail="No workspace")
    q = select(AuditLog).where(AuditLog.workspace_id == current_user.workspace_id)
    if action:
        q = q.where(AuditLog.action == action)
    q = q.order_by(desc(AuditLog.created_at)).limit(min(limit, 200))
    logs = db.scalars(q).all()
    return [
        AuditLogOut(
            id=str(log.id),
            action=log.action,
            user_id=str(log.user_id) if log.user_id else None,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            metadata=log.extra_data,
            created_at=log.created_at,
        )
        for log in logs
    ]
