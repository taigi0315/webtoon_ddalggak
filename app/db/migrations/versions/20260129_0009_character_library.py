"""Add character library fields.

Revision ID: 20260129_0009
Revises: 20260129_0008_character_variant_suggestions
Create Date: 2026-01-29

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260129_0009"
down_revision = "20260129_0008"

branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("generation_prompt", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("is_library_saved", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("characters", "is_library_saved")
    op.drop_column("characters", "generation_prompt")
