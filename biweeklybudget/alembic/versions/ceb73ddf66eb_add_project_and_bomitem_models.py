"""Add Project and BoMItem models

Revision ID: ceb73ddf66eb
Revises: 8627a80874a6
Create Date: 2017-07-04 09:53:57.044088

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ceb73ddf66eb'
down_revision = '8627a80874a6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=True),
        sa.Column('notes', sa.String(length=254), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_projects')),
        mysql_engine='InnoDB'
    )
    op.create_table(
        'bom_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=254), nullable=True),
        sa.Column('notes', sa.String(length=254), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column(
            'unit_cost', sa.Numeric(precision=10, scale=4), nullable=True
        ),
        sa.Column('url', sa.String(length=254), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ['project_id'], ['projects.id'],
            name=op.f('fk_bom_items_project_id_projects')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bom_items')),
        mysql_engine='InnoDB'
    )


def downgrade():
    op.drop_table('projects')
    op.drop_table('bom_items')
