"""TxnReconcile allow txn_id to be null

Revision ID: 08b6358a04bf
Revises: 04e61490804b
Create Date: 2018-03-07 19:48:06.050926

"""
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '08b6358a04bf'
down_revision = '04e61490804b'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'txn_reconciles', 'txn_id',
        existing_type=mysql.INTEGER(display_width=11),
        nullable=True
    )


def downgrade():
    conn = op.get_bind()
    conn.execute("SET FOREIGN_KEY_CHECKS=0")
    op.alter_column(
        'txn_reconciles', 'txn_id',
        existing_type=mysql.INTEGER(display_width=11),
        nullable=False
    )
    conn.execute("SET FOREIGN_KEY_CHECKS=1")
