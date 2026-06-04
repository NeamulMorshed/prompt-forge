"""prompt library — add group_id, branched_from_version_id, title, created_at to prompts

Revision ID: 0003_prompt_library
Revises: 0002_context_profiles_phase2
Create Date: 2026-06-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_prompt_library"
down_revision: Union[str, Sequence[str], None] = "0002_context_profiles_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("prompts", sa.Column("group_id", sa.Uuid(), nullable=True))
    op.add_column("prompts", sa.Column("branched_from_version_id", sa.Uuid(), nullable=True))
    op.add_column("prompts", sa.Column("title", sa.String(), nullable=True))
    op.add_column(
        "prompts",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    # Backfill: existing rows get group_id = their own id (self-referencing root)
    op.execute("UPDATE prompts SET group_id = id")
    op.create_foreign_key(
        "fk_prompts_branched_from_version_id",
        "prompts",
        "prompt_versions",
        ["branched_from_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_prompts_group_id", "prompts", ["group_id"])
    op.create_index("ix_prompts_user_created", "prompts", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_prompts_user_created", table_name="prompts")
    op.drop_index("ix_prompts_group_id", table_name="prompts")
    op.drop_constraint("fk_prompts_branched_from_version_id", "prompts", type_="foreignkey")
    op.drop_column("prompts", "created_at")
    op.drop_column("prompts", "title")
    op.drop_column("prompts", "branched_from_version_id")
    op.drop_column("prompts", "group_id")
