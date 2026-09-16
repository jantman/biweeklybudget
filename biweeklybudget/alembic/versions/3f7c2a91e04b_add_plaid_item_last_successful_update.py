"""add PlaidItem last_successful_update

Revision ID: 3f7c2a91e04b
Revises: c5e3a9b1d7f2
Create Date: 2026-09-15 20:05:00.000000

Adds the plaid_items.last_successful_update column, holding the time Plaid
reports it last successfully updated transactions for that Item (GitHub issue
#268). The column is nullable: existing rows have no value, and none can be
backfilled because it can only come from Plaid. Items acquire it on their next
update. The downgrade drops it.

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utc.sqltypes import UtcDateTime


# revision identifiers, used by Alembic.
revision = '3f7c2a91e04b'
down_revision = 'c5e3a9b1d7f2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'plaid_items',
        sa.Column('last_successful_update', UtcDateTime(timezone=True),
                  nullable=True)
    )


def downgrade():
    op.drop_column('plaid_items', 'last_successful_update')
