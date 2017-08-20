"""
account interest and payoff attributes

Revision ID: 9dc8545963be
Revises: ceb73ddf66eb
Create Date: 2017-08-12 21:27:44.820078

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9dc8545963be'
down_revision = 'ceb73ddf66eb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'accounts',
        sa.Column(
            'apr',
            sa.Numeric(precision=5, scale=4),
            nullable=True
        )
    )
    op.add_column(
        'accounts',
        sa.Column(
            'prime_rate_margin',
            sa.Numeric(precision=5, scale=4),
            nullable=True
        )
    )
    op.add_column(
        'accounts',
        sa.Column(
            'interest_class_name',
            sa.String(length=70),
            nullable=True
        )
    )
    op.add_column(
        'accounts',
        sa.Column(
            'min_payment_class_name',
            sa.String(length=70),
            nullable=True
        )
    )


def downgrade():
    op.drop_column('accounts', 'min_payment_class_name')
    op.drop_column('accounts', 'interest_class_name')
    op.drop_column('accounts', 'prime_rate_margin')
    op.drop_column('accounts', 'apr')
