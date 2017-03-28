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

from sqlalchemy import (
    Column, Integer, String, ForeignKey, Numeric, UniqueConstraint
)
from sqlalchemy_utc import UtcDateTime
from sqlalchemy.orm import relationship
from biweeklybudget.models.base import Base, ModelAsDict


class OFXStatement(Base, ModelAsDict):

    __tablename__ = 'ofx_statements'
    __table_args__ = (
        UniqueConstraint('account_id', 'filename'),
        {'mysql_engine': 'InnoDB'}
    )

    #: Unique ID
    id = Column(Integer, primary_key=True)

    #: Foreign key - Account.id - ID of the account this statement is for
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)

    #: Relationship to the :py:class:`~.Account` this statement is for
    account = relationship(
        "Account", uselist=False
    )

    #: Filename parsed from
    filename = Column(String(254))

    #: File mtime
    file_mtime = Column(UtcDateTime)

    #: Currency definition ("USD")
    currency = Column(String(10))

    #: FID of the Institution
    bankid = Column(String(20))

    #: Routing Number
    routing_number = Column(String(20))

    #: Textual account type, from the bank (i.e. "Checking")
    acct_type = Column(String(32))

    #: BrokerID, for investment accounts
    brokerid = Column(String(30))

    #: Institution's account ID
    acctid = Column(String(30))

    #: Account Type, string corresponding to ofxparser.ofxparser.AccountType
    type = Column(String(20))

    #: Last OFX statement datetime
    as_of = Column(UtcDateTime)

    #: Ledger balance, or investment account value
    ledger_bal = Column(Numeric(precision=10, scale=4))

    #: as-of date for the ledger balance
    ledger_bal_as_of = Column(UtcDateTime)

    #: Available balance
    avail_bal = Column(Numeric(precision=10, scale=4))

    #: as-of date for the available balance
    avail_bal_as_of = Column(UtcDateTime)

    def __repr__(self):
        return "<OFXStatement(id=%s, account_id=%s, as_of='%s')>" % (
            self.id, self.account_id, self.as_of
        )
