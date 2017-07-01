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

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, ForeignKey, SmallInteger, Numeric
)
from sqlalchemy.orm import relationship
from biweeklybudget.models.base import Base, ModelAsDict
from biweeklybudget.utils import dtnow


class Vehicle(Base, ModelAsDict):

    __tablename__ = 'vehicles'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Name of vehicle
    name = Column(String(254))

    #: whether active or historical
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return "<Vehicle(id=%s, name=%s)>" % (
            self.id, self.name
        )


class FuelFill(Base, ModelAsDict):

    __tablename__ = 'fuellog'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: date of the fill
    date = Column(Date, default=dtnow().date())

    #: ID of the vehicle
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'))

    #: The vehicle
    vehicle = relationship(
        "Vehicle", backref="fuellog", uselist=False
    )

    #: Odometer reading of the vehicle, in miles
    odometer_miles = Column(Integer)

    #: Number of miles the vehicle thinks it's traveled since the last fill.
    traveled_miles = Column(SmallInteger)

    #: Fuel level before fill, as a percentage (Integer 0-100)
    level_before = Column(SmallInteger)

    #: Fuel level after fill, as a percentage (Integer 0-100)
    level_after = Column(SmallInteger)

    #: Location of fill - usually a gas station name/address
    fill_location = Column(String(254))

    #: Fuel cost per gallon
    cost_per_gallon = Column(Numeric(precision=10, scale=4))

    #: Total cost of fill
    total_cost = Column(Numeric(precision=10, scale=4))

    #: Total amount of fuel (gallons)
    gallons = Column(Numeric(precision=10, scale=4))

    #: MPG as reported by the vehicle itself
    reported_mpg = Column(Numeric(precision=10, scale=4))

    #: Notes
    notes = Column(String(254))

    def __repr__(self):
        return "<FuelFill(id=%s, vehicle=%s, date=%s)>" % (
            self.id, self.vehicle_id, self.date
        )
