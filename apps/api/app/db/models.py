import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# SQLAlchemy 2.0 generic Uuid: native UUID on Postgres, CHAR(32) on SQLite (tests).
def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


# Use JSONB on Postgres, plain JSON elsewhere (e.g., SQLite in unit tests).
_Json = JSON().with_variant(JSONB, "postgresql")


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    plan: Mapped[str] = mapped_column(String, default="free")
    preferences: Mapped[dict | None] = mapped_column(_Json, nullable=True)
    locale: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workspaces.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String)
    seats: Mapped[int] = mapped_column(Integer, default=1)
    governance_settings: Mapped[dict | None] = mapped_column(_Json, nullable=True)


class ContextProfile(Base):
    __tablename__ = "context_profiles"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workspaces.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String)
    context_json: Mapped[dict | None] = mapped_column(_Json, nullable=True)


class DomainPack(Base):
    __tablename__ = "domain_packs"
    id: Mapped[uuid.UUID] = _pk()
    domain: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[str] = mapped_column(String)
    crs_json: Mapped[dict | None] = mapped_column(_Json, nullable=True)
    framing_json: Mapped[dict | None] = mapped_column(_Json, nullable=True)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    initial_input: Mapped[str | None] = mapped_column(String, nullable=True)
    filled_slots: Mapped[dict | None] = mapped_column(_Json, nullable=True)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    ccs: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[uuid.UUID] = _pk()
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sessions.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    model_target: Mapped[str | None] = mapped_column(String, nullable=True)
    skills_applied: Mapped[dict | None] = mapped_column(_Json, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: Mapped[uuid.UUID] = _pk()
    prompt_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("prompts.id"))
    content: Mapped[str] = mapped_column(String)
    score_json: Mapped[dict | None] = mapped_column(_Json, nullable=True)
    outcome_label: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutcomeRating(Base):
    __tablename__ = "outcome_ratings"
    id: Mapped[uuid.UUID] = _pk()
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("prompt_versions.id")
    )
    rating: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[str | None] = mapped_column(String, nullable=True)
    skills_applied: Mapped[dict | None] = mapped_column(_Json, nullable=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    ccs_at_gen: Mapped[float | None] = mapped_column(Float, nullable=True)


class Pattern(Base):
    __tablename__ = "patterns"
    id: Mapped[uuid.UUID] = _pk()
    domain: Mapped[str] = mapped_column(String, index=True)
    structure_json: Mapped[dict | None] = mapped_column(_Json, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
