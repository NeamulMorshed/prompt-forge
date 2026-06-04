from datetime import datetime

from pydantic import BaseModel


class VersionSummary(BaseModel):
    id: str
    content_preview: str
    score: float | None
    outcome_label: str | None
    created_at: datetime


class PromptGroupOut(BaseModel):
    group_id: str
    root_prompt_id: str
    title: str | None
    domain: str | None
    version_count: int
    latest_version: VersionSummary
    created_at: datetime


class VersionDetailOut(BaseModel):
    id: str
    content: str
    score_json: dict | None
    outcome_label: str | None
    created_at: datetime


class PromptDetailOut(BaseModel):
    id: str
    group_id: str
    title: str | None
    domain: str | None
    skills_applied: list[str] | None
    score: float | None
    branched_from_version_id: str | None
    created_at: datetime
    versions: list[VersionDetailOut]


class PromptGroupDetailOut(BaseModel):
    group_id: str
    prompts: list[PromptDetailOut]


class PatchTitleRequest(BaseModel):
    title: str


class PatchLabelRequest(BaseModel):
    outcome_label: str | None = None


class OkResponse(BaseModel):
    ok: bool
