"""
add DB settings table

Revision ID: 32b34a664b5a
Revises: 9dc8545963be
Create Date: 2017-08-12 21:44:45.860272

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32b34a664b5a'
down_revision = '9dc8545963be'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'settings',
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.Column('is_json', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('name', name=op.f('pk_settings')),
        mysql_engine='InnoDB'
    )


def downgrade():
    op.drop_table('settings')
