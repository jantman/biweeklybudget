"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2020 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

import logging
from sqlalchemy import (
    Column, String, PrimaryKeyConstraint, ForeignKey
)
from sqlalchemy.orm import relationship

from biweeklybudget.models.base import Base, ModelAsDict

logger = logging.getLogger(__name__)


class PlaidAccount(Base, ModelAsDict):

    __tablename__ = 'plaid_accounts'
    __table_args__ = (
        PrimaryKeyConstraint('item_id', 'account_id'),
        {'mysql_engine': 'InnoDB'}
    )

    #: Plaid Item ID
    item_id = Column(
        String(70), ForeignKey('plaid_items.item_id'), nullable=False
    )

    #: Plaid Account ID
    account_id = Column(String(70), nullable=False)

    #: PlaidItem this PlaidAccount is associated with
    plaid_item = relationship('PlaidItem', uselist=False)

    #: Name of the account
    name = Column(String(100))

    #: mask
    mask = Column(String(20))

    #: Plaid account type
    account_type = Column(String(50))

    #: Plaid account subtype
    account_subtype = Column(String(50))

    def __repr__(self):
        return "<PlaidAccount(item_id=%s, account_id=%s)>" % (
            self.item_id, self.account_id
        )
