"""add omit_from_graphs boolean to Budget model

Revision ID: 6d37400ea9cd
Revises: 61e62ef50513
Create Date: 2017-11-11 07:45:36.580049

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d37400ea9cd'
down_revision = '61e62ef50513'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'budgets',
        sa.Column('omit_from_graphs', sa.Boolean(), nullable=True)
    )


def downgrade():
    op.drop_column('budgets', 'omit_from_graphs')
