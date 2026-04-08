"""create prompts table

Revision ID: 854ef5d894ba
Revises:
Create Date: 2026-04-09 01:45:25.721108

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '854ef5d894ba'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'prompts',
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('model', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('task_type', sa.String(length=100), nullable=False),
        sa.Column('effectiveness', sa.Integer(), nullable=False),
        sa.Column('tags', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('prompts')
