"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2017 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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
    Column, Integer, String, ForeignKey, Numeric, Boolean, inspect, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from biweeklybudget.models.base import Base, ModelAsDict

logger = logging.getLogger(__name__)


class Project(Base, ModelAsDict):

    __tablename__ = 'projects'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Name of project
    name = Column(String(40))

    #: Notes / Description
    notes = Column(String(254))

    #: whether active or historical
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return "<Project(id=%s, name=%s)>" % (
            self.id, self.name
        )

    @property
    def total_cost(self):
        """
        Return the total cost of all line items (:py:class:`~.BoMItem`) for
        this project.

        :return: total cost of this project
        :rtype: float
        """
        sess = inspect(self).session
        cost = sess.query(BoMItem).filter(
            BoMItem.project_id.__eq__(self.id)
        ).with_entities(
            func.sum(BoMItem.line_cost)
        ).scalar()
        if cost is None:
            return 0.0
        return float(cost)

    @property
    def remaining_cost(self):
        """
        Return the remaining cost of all line items (:py:class:`~.BoMItem`) for
        this project which are still active

        :return: remianing cost of this project
        :rtype: float
        """
        sess = inspect(self).session
        cost = sess.query(BoMItem).filter(
            BoMItem.project_id.__eq__(self.id),
            BoMItem.is_active.__eq__(True)
        ).with_entities(
            func.sum(BoMItem.line_cost)
        ).scalar()
        if cost is None:
            return 0.0
        return float(cost)


class BoMItem(Base, ModelAsDict):
    __tablename__ = 'bom_items'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Project ID
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    #: Relationship to the :py:class:`~.Project` this item is for
    project = relationship('Project', uselist=False)

    #: Name of item
    name = Column(String(254))

    #: Notes / Description
    notes = Column(String(254))

    #: Quantity Required
    quantity = Column(Integer, default=1)

    #: Unit Cost / Cost Each
    unit_cost = Column(Numeric(precision=10, scale=4), default=0.0)

    #: URL
    url = Column(String(254))

    #: whether active or historical
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return "<BoMItem(id=%s, name=%s, project_id=%s)>" % (
            self.id, self.name, self.project_id
        )

    @hybrid_property
    def line_cost(self):
        """
        The total cost for this BoM Item, unit_cost times quantity

        :return: total line cost
        :rtype: decimal.Decimal
        """
        return (self.quantity * 1.0) * self.unit_cost
