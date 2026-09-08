"""add budget_accounts table

Revision ID: 2d881fa466fe
Revises: f9df90273cdd
Create Date: 2026-09-08 18:25:08.105890

Adds the many-to-many association between standing Budgets and the Accounts
that physically hold their money, for the Cash Position page. See GitHub
issue #321 and biweeklybudget/models/budget_account_link.py.

The table is pure association: two foreign keys, no amount and no split.
ON DELETE CASCADE on both sides means deleting either a Budget or an Account
removes its association rows, so nothing can outlive the record it refers to.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d881fa466fe'
down_revision = 'f9df90273cdd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'budget_accounts',
        sa.Column('budget_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['account_id'], ['accounts.id'],
            name=op.f('fk_budget_accounts_account_id_accounts'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['budget_id'], ['budgets.id'],
            name=op.f('fk_budget_accounts_budget_id_budgets'),
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint(
            'budget_id', 'account_id', name=op.f('pk_budget_accounts')
        ),
        mysql_engine='InnoDB'
    )


def downgrade():
    op.drop_table('budget_accounts')
