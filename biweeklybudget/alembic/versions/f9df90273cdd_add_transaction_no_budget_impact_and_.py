"""add Transaction no_budget_impact and credit_payment_acct_id

Revision ID: f9df90273cdd
Revises: a1b2c3d4e5f6
Create Date: 2026-09-06 18:00:25.160750

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9df90273cdd'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows get no_budget_impact = 0 (false) and
    # credit_payment_acct_id = NULL, so every existing Transaction keeps
    # exactly the budget impact it has today.
    op.add_column('transactions', sa.Column('no_budget_impact', sa.Boolean(), nullable=False))
    op.add_column('transactions', sa.Column('credit_payment_acct_id', sa.Integer(), nullable=True))
    op.create_foreign_key(op.f('fk_transactions_credit_payment_acct_id_accounts'), 'transactions', 'accounts', ['credit_payment_acct_id'], ['id'])


def downgrade():
    # The foreign key constraint must be dropped BEFORE the column it
    # references; MySQL refuses to drop a column that a constraint still
    # references.
    op.drop_constraint(op.f('fk_transactions_credit_payment_acct_id_accounts'), 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'credit_payment_acct_id')
    op.drop_column('transactions', 'no_budget_impact')
