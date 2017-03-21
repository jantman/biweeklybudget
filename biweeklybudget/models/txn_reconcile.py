"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of biweeklybudget, also known as biweeklybudget.

    biweeklybudget is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    biweeklybudget is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with biweeklybudget.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/biweeklybudget> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

from biweeklybudget.utils import dtnow
from sqlalchemy import Column, Integer, String, ForeignKey, ForeignKeyConstraint
from sqlalchemy_utc import UtcDateTime
from sqlalchemy.orm import relationship
from biweeklybudget.models.base import Base, ModelAsDict


class TxnReconcile(Base, ModelAsDict):

    __tablename__ = 'txn_reconciles'
    __table_args__ = (
        ForeignKeyConstraint(
            ['ofx_account_id', 'ofx_fitid'],
            ['ofx_trans.account_id', 'ofx_trans.fitid']
        ),
        {'mysql_engine': 'InnoDB'}
    )

    # Primary Key
    id = Column(Integer, primary_key=True)

    txn_id = Column(Integer, ForeignKey('transactions.id'))
    transaction = relationship(
        "Transaction", backref="reconcile", uselist=False,
        foreign_keys=[txn_id]
    )

    ofx_fitid = Column(String(255))
    ofx_account_id = Column(Integer)
    ofx_trans = relationship(
        "OFXTransaction", backref="reconcile", uselist=False,
        foreign_keys=[ofx_fitid, ofx_account_id]
    )

    rule_id = Column(Integer, ForeignKey('reconcile_rules.id'))
    rule = relationship("ReconcileRule")

    note = Column(String(254))

    reconciled_at = Column(UtcDateTime, default=dtnow())

    def __repr__(self):
        return "<TxnReconcile(id=%d)>" % (
            self.id
        )
