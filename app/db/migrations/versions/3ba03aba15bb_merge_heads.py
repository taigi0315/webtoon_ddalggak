"""merge heads

Revision ID: 3ba03aba15bb
Revises: 20260130_0003, 731b543c5390
Create Date: 2026-01-30 17:22:20.811257

"""

from alembic import op
import sqlalchemy as sa


revision = '3ba03aba15bb'
down_revision = ('20260130_0003', '731b543c5390')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
