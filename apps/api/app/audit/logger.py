import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger("app.audit")


def log_event(
    db: Session,
    action: str,
    user_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        from app.db.models import AuditLog
        entry = AuditLog(
            id=uuid.uuid4(),
            action=action,
            user_id=user_id,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=metadata,
        )
        db.add(entry)
    except Exception as exc:
        logger.warning("Audit log write failed (non-fatal): %s", exc)
