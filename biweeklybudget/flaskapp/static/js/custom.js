/*
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016-2024 Jason Antman <http://www.jasonantman.com>

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
*/

/**
 * Format a null object as "&nbsp;"
 *
 * @param {(Object|null)} o - input value
 * @returns {(Object|string)} o if not null, ``&nbsp;`` if null
 */
function fmt_null(o) {
    if ( o === null ) {
        return '&nbsp;';
    }
    return o;
}

/**
 * Format a float as currency. If ``value`` is null, return ``&nbsp;``.
 * Otherwise, construct a new instance of ``Intl.NumberFormat`` and use it to
 * format the currency to a string. The formatter is called with the
 * ``LOCALE_NAME`` and ``CURRENCY_CODE`` variables, which are templated into
 * the header of ``base.html`` using the values specified in the Python
 * settings module.
 *
 * @param {number} value - the number to format
 * @returns {string} The number formatted as currency
 */
function fmt_currency(value) {
    if (value === null) { return '&nbsp;'; }
    return new Intl.NumberFormat(
      LOCALE_NAME, { style: 'currency', currency: CURRENCY_CODE }
    ).format(value);
}

/**
 * Format a javascript Date as ISO8601 YYYY-MM-DD
 *
 * @param {Date} d - the date to format
 * @returns {string} YYYY-MM-DD
 */
function isoformat(d) {
  var mm = d.getMonth() + 1; // getMonth() is zero-based
  var dd = d.getDate();

  return [d.getFullYear(),
          (mm>9 ? '' : '0') + mm,
          (dd>9 ? '' : '0') + dd
         ].join('-');
}
