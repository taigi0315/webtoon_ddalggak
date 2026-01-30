"""Global actors - make project_id nullable on characters.

Revision ID: 20260130_0002
Revises: 20260130_0001
Create Date: 2026-01-30

Actors (characters in the library) can now exist without a project,
making them truly global and reusable across different projects.
"""

import sqlalchemy as sa
from alembic import op


revision = "20260130_0002"
down_revision = "20260130_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make project_id nullable on characters for global actors
    with op.batch_alter_table("characters") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )


def downgrade() -> None:
    # Make project_id required again
    # Note: This may fail if NULL values exist - manual cleanup required
    with op.batch_alter_table("characters") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
