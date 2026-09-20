"""add Account omit_from_graphs

Revision ID: 8a3d61c0fe57
Revises: 3f7c2a91e04b
Create Date: 2026-09-19 19:45:00.000000

Adds the accounts.omit_from_graphs column, a per-Account flag that keeps an
Account off charts that plot accounts -- today, the Account Balances chart on
the index page (GitHub issue #357). It mirrors budgets.omit_from_graphs, added
by revision 6d37400ea9cd.

The column is nullable and carries no server default, matching the model's
``Column(Boolean, default=False)``, whose default is applied Python-side on
insert. Existing rows therefore acquire NULL, which every reader treats as
"not omitted", so the upgrade changes nothing about which Accounts are
plotted. Note that this makes the reading filter's spelling load-bearing:
``omit_from_graphs IS NOT true`` includes the NULL rows, whereas
``omit_from_graphs = false`` would exclude them and blank the chart.

The downgrade drops the column, discarding the flags. Nothing else records
them, and no financial data is involved.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a3d61c0fe57'
down_revision = '3f7c2a91e04b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'accounts',
        sa.Column('omit_from_graphs', sa.Boolean(), nullable=True)
    )


def downgrade():
    op.drop_column('accounts', 'omit_from_graphs')
