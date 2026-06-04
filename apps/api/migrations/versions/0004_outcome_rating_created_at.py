"""Add created_at to outcome_ratings

Revision ID: 0004_outcome_rating_created_at
Revises: 0003_prompt_library
Create Date: 2026-06-04 23:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_outcome_rating_created_at"
down_revision = "0003_prompt_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outcome_ratings",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("outcome_ratings", "created_at")
