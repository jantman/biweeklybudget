"""Account add do_not_reconcile boolean

Revision ID: ed827c515edb
Revises: 5446559aecf7
Create Date: 2017-04-29 09:46:33.057376

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ed827c515edb'
down_revision = '5446559aecf7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'accounts',
        sa.Column(
            'reconcile_trans',
            sa.Boolean(),
            nullable=False,
            default=True
        )
    )


def downgrade():
    op.drop_column('accounts', 'reconcile_trans')
