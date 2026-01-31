"""remove story style fields

Revision ID: 20260130_0003
Revises: 20260130_0002
Create Date: 2026-01-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260130_0003'
down_revision = '20260130_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove story_style fields from Story table
    with op.batch_alter_table('stories', schema=None) as batch_op:
        batch_op.drop_column('default_story_style')

    # Remove story_style_override from Scene table
    with op.batch_alter_table('scenes', schema=None) as batch_op:
        batch_op.drop_column('story_style_override')

    # Remove default_story_style_id from Character table
    with op.batch_alter_table('characters', schema=None) as batch_op:
        batch_op.drop_column('default_story_style_id')

    # Remove story_style_id from CharacterVariant table
    with op.batch_alter_table('character_variants', schema=None) as batch_op:
        batch_op.drop_column('story_style_id')

    # Remove default_story_style from Episode table
    with op.batch_alter_table('episodes', schema=None) as batch_op:
        batch_op.drop_column('default_story_style')


def downgrade() -> None:
    # Add back default_story_style to Episode table
    with op.batch_alter_table('episodes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_story_style', sa.String(length=64), nullable=False, server_default='default'))

    # Add back story_style_id to CharacterVariant table
    with op.batch_alter_table('character_variants', schema=None) as batch_op:
        batch_op.add_column(sa.Column('story_style_id', sa.String(length=64), nullable=True))

    # Add back default_story_style_id to Character table
    with op.batch_alter_table('characters', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_story_style_id', sa.String(length=64), nullable=True))

    # Add back story_style_override to Scene table
    with op.batch_alter_table('scenes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('story_style_override', sa.String(length=64), nullable=True))

    # Add back default_story_style to Story table
    with op.batch_alter_table('stories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_story_style', sa.String(length=64), nullable=False, server_default='default'))
