"""add standing_budget_id to projects

Revision ID: a1b2c3d4e5f6
Revises: d01774fa3ae3
Create Date: 2026-02-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd01774fa3ae3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'projects',
        sa.Column('standing_budget_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_projects_standing_budget_id',
        'projects', 'budgets',
        ['standing_budget_id'], ['id']
    )


def downgrade():
    op.drop_constraint(
        'fk_projects_standing_budget_id',
        'projects',
        type_='foreignkey'
    )
    op.drop_column('projects', 'standing_budget_id')
