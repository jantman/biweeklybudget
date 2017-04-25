"""txnreconcile unique constraints

Revision ID: f136418fc4ab
Revises: a8f1228af250
Create Date: 2017-04-25 17:23:48.322303

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f136418fc4ab'
down_revision = 'a8f1228af250'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        op.f('uq_txn_reconciles_ofx_account_id'),
        'txn_reconciles',
        ['ofx_account_id', 'ofx_fitid']
    )
    op.create_unique_constraint(
        op.f('uq_txn_reconciles_txn_id'),
        'txn_reconciles',
        ['txn_id']
    )


def downgrade():
    op.drop_constraint(
        op.f('uq_txn_reconciles_txn_id'),
        'txn_reconciles',
        type_='unique'
    )
    op.drop_constraint(
        op.f('uq_txn_reconciles_ofx_account_id'),
        'txn_reconciles',
        type_='unique'
    )
