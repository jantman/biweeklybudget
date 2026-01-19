"""add weekly and annual scheduled transaction types

Revision ID: bbb39e1d7c5d
Revises: 1bb9e6a1c07c
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bbb39e1d7c5d'
down_revision = '1bb9e6a1c07c'
branch_labels = None
depends_on = None


def upgrade():
    # Add day_of_week column for weekly scheduled transactions (0=Monday, 6=Sunday)
    op.add_column(
        'scheduled_transactions',
        sa.Column('day_of_week', sa.SmallInteger(), nullable=True)
    )
    # Add annual_month column for annual scheduled transactions (1-12)
    op.add_column(
        'scheduled_transactions',
        sa.Column('annual_month', sa.SmallInteger(), nullable=True)
    )
    # Add annual_day column for annual scheduled transactions (1-31)
    op.add_column(
        'scheduled_transactions',
        sa.Column('annual_day', sa.SmallInteger(), nullable=True)
    )


def downgrade():
    op.drop_column('scheduled_transactions', 'annual_day')
    op.drop_column('scheduled_transactions', 'annual_month')
    op.drop_column('scheduled_transactions', 'day_of_week')
