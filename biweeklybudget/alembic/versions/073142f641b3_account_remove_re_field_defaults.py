"""Account remove re field defaults

Revision ID: 073142f641b3
Revises: 08b6358a04bf
Create Date: 2018-03-08 09:25:17.673039

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String

Session = sessionmaker()

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = '073142f641b3'
down_revision = '08b6358a04bf'
branch_labels = None
depends_on = None


class Account(Base):

    __tablename__ = 'accounts'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: regex for matching transactions as interest charges
    re_interest_charge = Column(String(254))

    #: regex for matching transactions as interest paid
    re_interest_paid = Column(String(254))

    #: regex for matching transactions as payments
    re_payment = Column(String(254))

    #: regex for matching transactions as late fees
    re_fee = Column(String(254))


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    for acct in session.query(Account).all():
        acct.re_interest_charge = None
        acct.re_interest_paid = None
        acct.re_payment = None
        acct.re_fee = None
    session.commit()
    op.add_column(
        'accounts',
        sa.Column('re_late_fee', sa.String(length=254), nullable=True)
    )
    op.add_column(
        'accounts',
        sa.Column('re_other_fee', sa.String(length=254), nullable=True)
    )
    op.drop_column('accounts', 're_fee')


def downgrade():
    op.add_column(
        'accounts',
        sa.Column('re_fee', mysql.VARCHAR(length=254), nullable=True)
    )
    op.drop_column('accounts', 're_other_fee')
    op.drop_column('accounts', 're_late_fee')
    bind = op.get_bind()
    session = Session(bind=bind)
    for acct in session.query(Account).all():
        acct.re_interest_charge = '^(interest charge|purchase finance charge)'
        acct.re_interest_paid = '^interest paid'
        acct.re_payment = '^(online payment|' \
                          'internet payment|online pymt|payment)'
        acct.re_fee = '^(late fee|past due fee)'
    session.commit()
