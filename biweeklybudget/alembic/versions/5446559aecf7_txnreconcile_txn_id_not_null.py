"""TxnReconcile txn_id not null

Revision ID: 5446559aecf7
Revises: f136418fc4ab
Create Date: 2017-04-26 15:57:04.536291

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5446559aecf7'
down_revision = 'f136418fc4ab'
branch_labels = None
depends_on = None


def upgrade():
    # When making changes to a column that has a foreign key, we need to drop
    # and then re-add the constraint
    op.execute('DELETE FROM txn_reconciles WHERE txn_id IS NULL;')
    op.execute('LOCK TABLES txn_reconciles WRITE, transactions WRITE;')
    op.drop_constraint('fk_txn_reconciles_txn_id_transactions',
                       'txn_reconciles', type_='foreignkey')
    op.alter_column(
        'txn_reconciles',
        'txn_id',
        existing_type=mysql.INTEGER(display_width=11),
        nullable=False
    )
    op.create_foreign_key('fk_txn_reconciles_txn_id_transactions',
                          'txn_reconciles', 'transactions', ['txn_id'], ['id'])
    op.execute('UNLOCK TABLES;')


def downgrade():
    # When making changes to a column that has a foreign key, we need to drop
    # and then re-add the constraint
    op.execute('LOCK TABLES txn_reconciles WRITE, transactions WRITE;')
    op.drop_constraint('fk_txn_reconciles_txn_id_transactions',
                       'txn_reconciles', type_='foreignkey')
    op.alter_column(
        'txn_reconciles',
        'txn_id',
        existing_type=mysql.INTEGER(display_width=11),
        nullable=True
    )
    op.create_foreign_key('fk_txn_reconciles_txn_id_transactions',
                          'txn_reconciles', 'transactions', ['txn_id'], ['id'])
    op.execute('UNLOCK TABLES;')
