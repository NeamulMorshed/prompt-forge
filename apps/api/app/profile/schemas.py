from datetime import datetime

from pydantic import BaseModel, field_validator


class ProfileOut(BaseModel):
    id: str
    name: str
    core_context: dict[str, str]
    domain_overrides: dict[str, dict[str, str]]
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v) -> str:
        # Coerce UUID id to str for JSON serialisation
        return str(v)


class ProfileUpsert(BaseModel):
    core_context: dict[str, str] = {}
    domain_overrides: dict[str, dict[str, str]] = {}


class ExtractRequest(BaseModel):
    session_id: str


class ExtractOut(BaseModel):
    core_context: dict[str, str]
    domain_overrides: dict[str, dict[str, str]]
