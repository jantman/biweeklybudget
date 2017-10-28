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

from babel.numbers import get_currency_symbol

from biweeklybudget.flaskapp.app import app
from biweeklybudget.flaskapp.notifications import NotificationsController
from biweeklybudget import settings as settingsmod


@app.context_processor
def notifications():
    """
    Add notifications to template context for all templates.

    :return: template context with notifications added
    :rtype: dict
    """
    return dict(notifications=NotificationsController().get_notifications())


@app.context_processor
def settings():
    """
    Add settings to template context for all templates.

    :return: template context with settings added
    :rtype: dict
    """
    return {'settings': {x: getattr(settingsmod, x) for x in dir(settingsmod)}}


@app.context_processor
def utilities():
    """
    Utility functions to put in the jinja context.

    :return: template context with utility functions added
    :rtype: dict
    """
    def cast_float(x):
        return float(x)
    return dict(cast_float=cast_float)


@app.context_processor
def add_currency_symbol():
    """
    Context processor to inject the proper currency symbol into the Jinja2
    context as the "CURRENCY_SYM" variable.

    :return: proper currency symbol for our locale and currency
    :rtype: str
    """
    return dict(CURRENCY_SYM=get_currency_symbol(
        settingsmod.CURRENCY_CODE, locale=settingsmod.LOCALE_NAME
    ))
