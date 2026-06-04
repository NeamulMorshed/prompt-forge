import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.base import get_db
from app.db.models import User, Workspace, WorkspaceMember
from app.workspace.schemas import InviteRequest, MemberOut, WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _get_user_workspace(user: User, db: Session) -> Workspace | None:
    if user.workspace_id is None:
        return None
    return db.get(Workspace, user.workspace_id)


def _get_user_role(user: User, workspace: Workspace, db: Session) -> str | None:
    member = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.workspace_id == workspace.id,
        )
    )
    return member.role if member else None


@router.post("", response_model=WorkspaceOut)
def create_workspace(
    body: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    if current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User already belongs to a workspace")
    ws = Workspace(id=uuid.uuid4(), name=body.name, seats=10)
    db.add(ws)
    db.flush()
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(member)
    current_user.workspace_id = ws.id
    db.commit()
    db.refresh(ws)
    return WorkspaceOut.model_validate(ws)


@router.get("/me", response_model=WorkspaceOut)
def get_my_workspace(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    ws = _get_user_workspace(current_user, db)
    if ws is None:
        raise HTTPException(status_code=404, detail="No workspace")
    return WorkspaceOut.model_validate(ws)


@router.get("/members", response_model=list[MemberOut])
def list_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MemberOut]:
    ws = _get_user_workspace(current_user, db)
    if ws is None:
        raise HTTPException(status_code=404, detail="No workspace")
    members = db.scalars(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id)
    ).all()
    result = []
    for m in members:
        user = db.get(User, m.user_id)
        result.append(MemberOut(
            user_id=m.user_id,
            email=user.email if user else "",
            role=m.role,
            joined_at=m.joined_at,
        ))
    return result


@router.post("/invite", response_model=dict)
def invite_member(
    body: InviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ws = _get_user_workspace(current_user, db)
    if ws is None:
        raise HTTPException(status_code=404, detail="No workspace")
    role = _get_user_role(current_user, ws, db)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can invite members")
    invited_user = db.scalar(select(User).where(User.email == body.email))
    if invited_user is None:
        raise HTTPException(status_code=404, detail=f"No user with email {body.email!r}")
    if invited_user.workspace_id:
        raise HTTPException(status_code=400, detail="User already in a workspace")
    existing = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == invited_user.id,
            WorkspaceMember.workspace_id == ws.id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already a member")
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=invited_user.id,
        role=body.role,
    )
    db.add(member)
    invited_user.workspace_id = ws.id
    db.commit()
    return {"ok": True}


@router.delete("/leave", status_code=204)
def leave_workspace(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    ws = _get_user_workspace(current_user, db)
    if ws is None:
        raise HTTPException(status_code=404, detail="No workspace")
    role = _get_user_role(current_user, ws, db)
    if role == "owner":
        other_owners = db.scalars(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.role == "owner",
                WorkspaceMember.user_id != current_user.id,
            )
        ).all()
        if not other_owners:
            raise HTTPException(status_code=400, detail="Transfer ownership before leaving")
    member = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.workspace_id == ws.id,
        )
    )
    if member:
        db.delete(member)
    current_user.workspace_id = None
    db.commit()
