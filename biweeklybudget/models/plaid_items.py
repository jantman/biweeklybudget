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
from sqlalchemy import Column, String
from sqlalchemy_utc import UtcDateTime
from sqlalchemy.orm import relationship

from biweeklybudget.models.base import Base, ModelAsDict

logger = logging.getLogger(__name__)


class PlaidItem(Base, ModelAsDict):

    __tablename__ = 'plaid_items'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key - plaid Item ID
    item_id = Column(String(70), primary_key=True)

    #: Plaid item access token
    access_token = Column(String(70))

    #: institution name
    institution_name = Column(String(100))

    #: institution ID
    institution_id = Column(String(50))

    #: When this item was last updated
    last_updated = Column(UtcDateTime)

    #: Relationship to all :py:class:`~.PlaidAccount` for this Item
    all_accounts = relationship(
        'PlaidAccount', order_by='PlaidAccount.account_id'
    )

    def __repr__(self):
        return "<PlaidItem(item_id=%s, institution_name='%s')>" % (
            self.item_id, self.institution_name
        )
