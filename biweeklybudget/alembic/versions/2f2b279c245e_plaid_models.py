"""plaid models

Revision ID: 2f2b279c245e
Revises: ac93b5c826a5
Create Date: 2020-04-10 20:58:14.782621

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy_utc.sqltypes import UtcDateTime

# revision identifiers, used by Alembic.
revision = '2f2b279c245e'
down_revision = 'ac93b5c826a5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'plaid_accounts',
        sa.Column('item_id', sa.String(length=70), nullable=False),
        sa.Column('account_id', sa.String(length=70), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('mask', sa.String(length=20), nullable=True),
        sa.Column('account_type', sa.String(length=50), nullable=True),
        sa.Column('account_subtype', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint(
            'item_id', 'account_id', name=op.f('pk_plaid_accounts')
        ),
        mysql_engine='InnoDB'
    )
    op.create_table(
        'plaid_items',
        sa.Column('item_id', sa.String(length=70), nullable=False),
        sa.Column('access_token', sa.String(length=70), nullable=True),
        sa.Column('institution_name', sa.String(length=100), nullable=True),
        sa.Column('institution_id', sa.String(length=50), nullable=True),
        sa.Column('last_updated', UtcDateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('item_id', name=op.f('pk_plaid_items')),
        mysql_engine='InnoDB'
    )
    op.add_column(
        'accounts',
        sa.Column('plaid_account_id', sa.String(length=70), nullable=True)
    )
    op.create_foreign_key(
        op.f('fk_accounts_plaid_item_id_plaid_accounts'),
        'accounts',
        'plaid_accounts',
        ['plaid_item_id', 'plaid_account_id'],
        ['item_id', 'account_id']
    )
    op.drop_column('accounts', 'plaid_token')
    op.create_index(
        'fk_txn_reconciles_ofx_account_id_ofx_trans',
        'txn_reconciles',
        ['ofx_account_id', 'ofx_fitid'],
        unique=False
    )
    op.create_index(
        'fk_txn_reconciles_txn_id_transactions',
        'txn_reconciles',
        ['txn_id'],
        unique=False
    )


def downgrade():
    op.drop_index(
        'fk_txn_reconciles_txn_id_transactions',
        table_name='txn_reconciles'
    )
    op.drop_index(
        'fk_txn_reconciles_ofx_account_id_ofx_trans',
        table_name='txn_reconciles'
    )
    op.add_column(
        'accounts',
        sa.Column('plaid_token', mysql.VARCHAR(length=70), nullable=True)
    )
    op.drop_constraint(
        op.f('fk_accounts_plaid_item_id_plaid_accounts'),
        'accounts',
        type_='foreignkey'
    )
    op.drop_column('accounts', 'plaid_account_id')
    op.drop_table('plaid_items')
    op.drop_table('plaid_accounts')
