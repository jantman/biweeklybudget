"""add skip_balance field to Budget model

Revision ID: 64dcc80b4b0c
Revises: 32b34a664b5a
Create Date: 2017-10-12 18:39:09.112929

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '64dcc80b4b0c'
down_revision = '32b34a664b5a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'budgets',
        sa.Column('skip_balance', sa.Boolean(), nullable=True)
    )


def downgrade():
    op.drop_column('budgets', 'skip_balance')
