"""remove ofxgetter account fields

Revision ID: c5e3a9b1d7f2
Revises: 2d881fa466fe
Create Date: 2026-09-14 06:30:00.000000

Drops the three Account columns that only configured OFX downloading via the
removed ofxgetter, Vault and ofxclient (GitHub issue #265): vault_creds_path,
ofxgetter_config_json and ofx_cat_memo_to_name. The downgrade restores them,
empty, with their original types and positions.

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c5e3a9b1d7f2'
down_revision = '2d881fa466fe'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('accounts', 'ofxgetter_config_json')
    op.drop_column('accounts', 'vault_creds_path')
    op.drop_column('accounts', 'ofx_cat_memo_to_name')


def downgrade():
    # raw SQL so the columns go back to their original positions
    op.execute(
        'ALTER TABLE accounts '
        'ADD COLUMN ofx_cat_memo_to_name BOOL NULL AFTER description, '
        'ADD COLUMN vault_creds_path VARCHAR(254) NULL '
        'AFTER ofx_cat_memo_to_name, '
        'ADD COLUMN ofxgetter_config_json TEXT NULL AFTER vault_creds_path'
    )
