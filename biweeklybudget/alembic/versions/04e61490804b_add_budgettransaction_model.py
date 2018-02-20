"""add BudgetTransaction model

Revision ID: 04e61490804b
Revises: 6d37400ea9cd
Create Date: 2018-01-12 18:43:14.983133

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, Integer, ForeignKey, Numeric
import logging

logger = logging.getLogger(__name__)

Session = sessionmaker()

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = '04e61490804b'
down_revision = '6d37400ea9cd'
branch_labels = None
depends_on = None


class Transaction(Base):

    __tablename__ = 'transactions'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Actual amount of the transaction
    actual_amount = Column(Numeric(precision=10, scale=4), nullable=False)

    #: Budgeted amount of the transaction, if it was budgeted ahead of time
    #: via a :py:class:`~.ScheduledTransaction`.
    budgeted_amount = Column(Numeric(precision=10, scale=4))

    #: ID of the Budget this transaction is against
    budget_id = Column(Integer, ForeignKey('budgets.id'))

    #: ID of the Budget this transaction was planned to be funded by, if it
    #: was planned ahead via a :py:class:`~.ScheduledTransaction`
    planned_budget_id = Column(Integer, ForeignKey('budgets.id'))

    def __repr__(self):
        return "<Transaction(id=%s)>" % (
            self.id
        )


class BudgetTransaction(Base):
    """
    Represents the portion (amount) of a Transaction that is allocated
    against a specific budget. There will be one or more BudgetTransactions
    associated with each :py:class:`~.Transaction`.
    """

    __tablename__ = 'budget_transactions'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Amount of the transaction against this budget
    amount = Column(Numeric(precision=10, scale=4), nullable=False)

    #: ID of the Transaction this is part of
    trans_id = Column(Integer, ForeignKey('transactions.id'))

    #: Relationship - the :py:class:`~.Transaction` this is part of
    transaction = relationship(
        "Transaction", backref="budget_transactions", uselist=False
    )

    #: ID of the Budget this transaction is against
    budget_id = Column(Integer, ForeignKey('budgets.id'))

    def __repr__(self):
        return "<BudgetTransaction(id=%s)>" % (
            self.id
        )


class Budget(Base):

    __tablename__ = 'budgets'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)


def upgrade():
    op.create_table(
        'budget_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('trans_id', sa.Integer(), nullable=True),
        sa.Column('budget_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['budget_id'], ['budgets.id'],
            name=op.f('fk_budget_transactions_budget_id_budgets')
        ),
        sa.ForeignKeyConstraint(
            ['trans_id'], ['transactions.id'],
            name=op.f('fk_budget_transactions_trans_id_transactions')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_budget_transactions')),
        mysql_engine='InnoDB'
    )
    op.add_column(
        'transactions',
        sa.Column('planned_budget_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        op.f('fk_transactions_planned_budget_id_budgets'),
        'transactions', 'budgets', ['planned_budget_id'], ['id']
    )
    # Copy amount and budget_id from each existing Transaction to a
    # corresponding BudgetTransaction
    bind = op.get_bind()
    session = Session(bind=bind)
    for txn in session.query(Transaction).all():
        b = BudgetTransaction(
            amount=txn.actual_amount,
            trans_id=txn.id,
            budget_id=txn.budget_id
        )
        session.add(b)
        if txn.budgeted_amount is not None:
            txn.planned_budget_id = txn.budget_id
            session.add(txn)
    session.commit()
    op.drop_constraint(
        'fk_transactions_budget_id_budgets', 'transactions', type_='foreignkey'
    )
    op.drop_column('transactions', 'budget_id')
    op.drop_column('transactions', 'actual_amount')


def downgrade():
    op.add_column(
        'transactions',
        sa.Column(
            'budget_id',
            sa.Integer(),
            autoincrement=False,
            nullable=True
        )
    )
    op.create_foreign_key(
        'fk_transactions_budget_id_budgets',
        'transactions', 'budgets', ['budget_id'], ['id']
    )
    op.add_column(
        'transactions',
        sa.Column(
            'actual_amount',
            Numeric(precision=10, scale=4),
            nullable=False
        )
    )
    # migrate budget_transactions back to Transaction.budget_id
    bind = op.get_bind()
    session = Session(bind=bind)
    for txn in session.query(Transaction).all():
        bt = txn.budget_transactions[0]
        txn.budget_id = bt.budget_id
        txn.actual_amount = bt.amount
        session.add(txn)
    session.commit()
    op.drop_table('budget_transactions')
    op.drop_constraint(
        op.f('fk_transactions_planned_budget_id_budgets'),
        'transactions',
        type_='foreignkey'
    )
    op.drop_column('transactions', 'planned_budget_id')
