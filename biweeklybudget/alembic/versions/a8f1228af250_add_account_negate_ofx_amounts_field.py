"""add Account negate_ofx_amounts field

Revision ID: a8f1228af250
Revises: 7477ff15e8c4
Create Date: 2017-04-19 22:20:31.876889

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8f1228af250'
down_revision = '7477ff15e8c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('accounts', sa.Column('negate_ofx_amounts', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('accounts', 'negate_ofx_amounts')
