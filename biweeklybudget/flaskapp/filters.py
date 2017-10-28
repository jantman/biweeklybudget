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

from jinja2.runtime import Undefined
from humanize import naturaltime

from biweeklybudget.utils import dtnow, fmt_currency
from biweeklybudget.flaskapp.app import app
from biweeklybudget.models.account import AcctType


@app.template_filter('period_panel_color')
def period_panel_color_filter(x):
    """
    Given the remaining amount for a pay period, return "red" if less than
    zero, "yellow" if less than 100, or otherwise "green".

    :param x: PayPeriod remaining amount
    :type x: float
    :return: "red", "yellow" or "green"
    :rtype: str
    """
    if x <= 0:
        return "red"
    if x < 100:
        return "yellow"
    return "green"


@app.template_filter('dateymd')
def dateymd_filter(dt):
    """
    Format a datetime using %Y-%m-%d

    :param dt: datetime to format
    :type dt: datetime.datetime
    :return: formatted date
    :rtype: str
    """
    try:
        return dt.strftime('%Y-%m-%d')
    except AttributeError:
        return ''


@app.template_filter('isodate')
def isodate_filter(dt):
    """
    Format a datetime using %Y-%m-%d %H:%M:%S

    :param dt: datetime to format
    :type dt: datetime.datetime
    :return: formatted date
    :rtype: str
    """
    try:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except AttributeError:
        return ''


@app.template_filter('ago')
def ago_filter(dt):
    """
    Format a datetime using humanize.naturaltime, "ago"

    :param dt: datetime to compare to now
    :type dt: datetime.datetime
    :return: ago string
    :rtype: str
    """
    if dt == '' or dt is None or isinstance(dt, Undefined):
        return ''
    return naturaltime(dtnow() - dt)


@app.template_filter('dollars')
def dollars_filter(x):
    """
    Format as currency using :py:func:`~.utils.fmt_currency`.

    :param x: currency amount, int, float, decimal, etc.
    :return: formatted currency
    :rtype: str
    """
    if x == '' or x is None or isinstance(x, Undefined):
        return ''
    return fmt_currency(x)


@app.template_filter('reddollars')
def reddollars_filter(x):
    """
    Return a string similar to ``dollars_filter`` but in red text
    if negative.

    :param x: dollar amount, int, float, decimal, etc.
    :return: formatted currency
    :rtype: str
    """
    s = dollars_filter(x)
    if x < 0:
        s = '<span class="text-danger">%s</span>' % s
    return s


@app.template_filter('pluralize')
def pluralize_filter(word, number=1):
    """
    If number is greater than one, return word with an "s" appended, else
    return word unmodified.

    :param word: the word to pluralize or not
    :type word: string
    :param number: the number to check for greater-than-one-ness
    :type number: int
    :return: word, pluralized or not
    :rtype: str
    """
    if number > 1:
        return word + 's'
    return word


@app.template_filter('acct_icon')
def acct_icon_filter(acct):
    """
    Given an Account, return the proper classes for an account type icon for it.

    :param acct: the account
    :type acct: biweeklybudget.models.account.Account
    :return: string icon classes
    :rtype: str
    """
    if acct.acct_type == AcctType.Bank:
        return 'fa fa-bank fa-fw'
    if acct.acct_type == AcctType.Credit:
        return 'fa fa-credit-card fa-fw'
    if acct.acct_type == AcctType.Investment:
        return 'glyphicon glyphicon-piggy-bank'
    if acct.acct_type == AcctType.Cash:
        return 'fa fa-dollar fa-fw'


@app.template_filter('decimal_to_percent')
def decimal_to_percent(d):
    if d is None:
        return ''
    d = d * 100
    return '%.2f%%' % d


@app.template_filter('dict_to_class_args')
def dict_to_class_args(j):
    if 'args' not in j and 'kwargs' not in j:
        return ''
    args = j.get('args', [])
    s = ', '.join(['%s' % a for a in args])
    kwargs = j.get('kwargs', {})
    s += ', '.join(['%s=%s' % (k, kwargs[k]) for k in kwargs.keys()])
    return s


@app.template_filter('monthsyears')
def monthsyears(num):
    if num < 12:
        return '%f months' % num
    return '%.1f years' % (num / 12.0)
