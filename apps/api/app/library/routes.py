import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.base import get_db
from app.db.models import Prompt, PromptVersion, User
from app.library.schemas import (
    OkResponse,
    PatchLabelRequest,
    PatchTitleRequest,
    PromptDetailOut,
    PromptGroupDetailOut,
    PromptGroupOut,
    VersionDetailOut,
    VersionSummary,
)

router = APIRouter(prefix="/library", tags=["library"])


def _assert_owns(prompt: Prompt | None, user: User) -> Prompt:
    if prompt is None or prompt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return prompt


@router.get("", response_model=list[PromptGroupOut])
def list_library(
    domain: str | None = None,
    scope: str = "personal",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PromptGroupOut]:
    if scope == "workspace" and user.workspace_id:
        stmt = select(Prompt).where(Prompt.workspace_id == user.workspace_id)
    else:
        stmt = select(Prompt).where(Prompt.user_id == user.id)
    if domain:
        stmt = stmt.where(Prompt.domain == domain)
    stmt = stmt.order_by(Prompt.created_at.desc())
    prompts = list(db.scalars(stmt).all())

    # Group by group_id in Python
    groups: dict[str, list[Prompt]] = {}
    for p in prompts:
        key = str(p.group_id) if p.group_id else str(p.id)
        groups.setdefault(key, []).append(p)

    result: list[PromptGroupOut] = []
    for group_id_str, group_prompts in groups.items():
        # Already ordered newest-first; oldest = root
        newest = group_prompts[0]
        root = group_prompts[-1]

        version = db.scalar(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == newest.id)
            .order_by(PromptVersion.created_at.desc())
            .limit(1)
        )
        if version is None:
            continue

        result.append(
            PromptGroupOut(
                group_id=group_id_str,
                root_prompt_id=str(root.id),
                title=root.title,
                domain=newest.domain,
                version_count=len(group_prompts),
                latest_version=VersionSummary(
                    id=str(version.id),
                    content_preview=version.content[:200],
                    score=newest.score,
                    outcome_label=version.outcome_label,
                    created_at=version.created_at,
                ),
                created_at=root.created_at,
            )
        )
    return result


@router.get("/{prompt_id}", response_model=PromptGroupDetailOut)
def get_prompt_group(
    prompt_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PromptGroupDetailOut:
    try:
        pid = uuid.UUID(prompt_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    prompt = _assert_owns(db.get(Prompt, pid), user)

    # Return all prompts in the same group
    if prompt.group_id:
        group_prompts = list(
            db.scalars(
                select(Prompt)
                .where(Prompt.group_id == prompt.group_id, Prompt.user_id == user.id)
                .order_by(Prompt.created_at.asc())
            ).all()
        )
        group_id_for_response = str(prompt.group_id)
    else:
        # Prompt has no group_id (pre-migration row) — treat as singleton group
        group_prompts = [prompt]
        group_id_for_response = str(prompt.id)

    prompt_details: list[PromptDetailOut] = []
    for p in group_prompts:
        versions = list(
            db.scalars(
                select(PromptVersion)
                .where(PromptVersion.prompt_id == p.id)
                .order_by(PromptVersion.created_at.asc())
            ).all()
        )
        prompt_details.append(
            PromptDetailOut(
                id=str(p.id),
                group_id=group_id_for_response,
                title=p.title,
                domain=p.domain,
                skills_applied=p.skills_applied,
                score=p.score,
                branched_from_version_id=str(p.branched_from_version_id) if p.branched_from_version_id else None,
                created_at=p.created_at,
                versions=[
                    VersionDetailOut(
                        id=str(v.id),
                        content=v.content,
                        score_json=v.score_json,
                        outcome_label=v.outcome_label,
                        created_at=v.created_at,
                    )
                    for v in versions
                ],
            )
        )

    return PromptGroupDetailOut(group_id=group_id_for_response, prompts=prompt_details)


@router.patch("/{prompt_id}", response_model=OkResponse)
def patch_prompt_title(
    prompt_id: str,
    body: PatchTitleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OkResponse:
    try:
        pid = uuid.UUID(prompt_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    prompt = _assert_owns(db.get(Prompt, pid), user)
    prompt.title = body.title
    db.commit()
    return OkResponse(ok=True)


@router.patch("/{prompt_id}/versions/{version_id}", response_model=OkResponse)
def patch_version_label(
    prompt_id: str,
    version_id: str,
    body: PatchLabelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OkResponse:
    try:
        pid = uuid.UUID(prompt_id)
        vid = uuid.UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _assert_owns(db.get(Prompt, pid), user)
    version = db.get(PromptVersion, vid)
    if version is None or version.prompt_id != pid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    version.outcome_label = body.outcome_label
    db.commit()
    return OkResponse(ok=True)


@router.delete("/{prompt_id}", response_model=OkResponse)
def delete_prompt(
    prompt_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OkResponse:
    try:
        pid = uuid.UUID(prompt_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    prompt = _assert_owns(db.get(Prompt, pid), user)
    for v in db.scalars(select(PromptVersion).where(PromptVersion.prompt_id == pid)).all():
        db.delete(v)
    db.delete(prompt)
    db.commit()
    return OkResponse(ok=True)
