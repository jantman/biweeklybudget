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
 * Return the digit grouping separator and decimal separator for
 * ``LOCALE_NAME``, i.e. ``[',', '.']`` for ``en-US`` and ``['.', ',']`` for
 * ``de-DE``. Determined from ``Intl.NumberFormat`` rather than hard-coded, so
 * that changing the Python ``LOCALE_NAME`` setting is all that is needed to
 * support another locale.
 *
 * @returns {Array} 2-element Array of [group separator, decimal separator]
 */
function currency_separators() {
    var group = ',';
    var decimal = '.';
    try {
        var parts = new Intl.NumberFormat(LOCALE_NAME).formatToParts(11111.1);
        for (var i = 0; i < parts.length; i++) {
            if (parts[i].type === 'group') { group = parts[i].value; }
            if (parts[i].type === 'decimal') { decimal = parts[i].value; }
        }
    } catch (e) {
        // fall back to the en-US defaults above
    }
    return [group, decimal];
}

/**
 * Parse a user-entered currency string to a Number, or ``null`` if it cannot
 * be unambiguously interpreted.
 *
 * This is the browser counterpart to :js:func:`fmt_currency`, and mirrors
 * ``biweeklybudget.utils.parse_currency()`` on the server; the server remains
 * the authority, and this function exists so that in-browser validation does
 * not reject values the server would accept. See GitHub issue #323.
 *
 * For ``en-US``, all of ``1234.56``, ``1,234.56``, ``1 234.56``,
 * ``$1,234.56`` and ``(1,234.56)`` are interpreted, and bare integers such as
 * ``123`` are accepted. Ambiguously grouped values such as ``10,00`` return
 * ``null`` rather than a guess.
 *
 * Returns ``null`` and not ``NaN`` deliberately: ``NaN`` comparisons silently
 * evaluate false, which is how ``parseFloat`` used to disable the Save button
 * with no visible reason.
 *
 * @param {string} value - the string to parse
 * @returns {(number|null)} the numeric value, or null if not interpretable
 */
function parse_currency(value) {
    if (typeof value !== 'string') { return null; }
    // normalize unicode spaces (NBSP, thin space, narrow NBSP, figure space)
    var s = value.replace(/[\t\u00a0\u2007\u2009\u202f]/g, ' ').trim();
    var negative = false;
    if (s.length > 1 && s.charAt(0) === '(' &&
        s.charAt(s.length - 1) === ')') {
        negative = true;
        s = s.substring(1, s.length - 1).trim();
    }
    // Strip currency symbol, ISO code and sign repeatedly until stable; a
    // single pass mis-handles "-$1,234.56".
    var tokens = [CURRENCY_SYMBOL, CURRENCY_CODE];
    var changed = true;
    while (changed && s !== '') {
        changed = false;
        for (var i = 0; i < tokens.length; i++) {
            var tok = tokens[i];
            if (!tok) { continue; }
            if (s.indexOf(tok) === 0) {
                s = s.substring(tok.length).trim();
                changed = true;
            } else if (s.length >= tok.length &&
                       s.lastIndexOf(tok) === s.length - tok.length) {
                s = s.substring(0, s.length - tok.length).trim();
                changed = true;
            }
        }
        if (s.charAt(0) === '-' || s.charAt(0) === '+') {
            if (s.charAt(0) === '-') { negative = !negative; }
            s = s.substring(1).trim();
            changed = true;
        }
    }
    if (s === '') { return null; }
    var seps = currency_separators();
    var group = seps[0];
    var decimal = seps[1];
    // Rewrite spaces used as grouping separators into the locale's own
    // grouping separator rather than deleting them, so that the grouping
    // check below applies to space-separated input too. Deleting them would
    // read "1 2 3" as 123.
    s = s.split(' ').join(group);
    var parts = s.split(decimal);
    if (parts.length > 2) { return null; }
    var intpart = parts[0];
    var fracpart = parts.length === 2 ? parts[1] : '';
    if (fracpart !== '' && !/^[0-9]+$/.test(fracpart)) { return null; }
    // ".5" is a valid amount; "." alone is not
    if (intpart === '' && fracpart === '') { return null; }
    if (intpart === '') { intpart = '0'; }
    // validate digit grouping: either no separators at all, or groups of
    // exactly 3 after a leading group of 1 to 3
    var groups = intpart.split(group);
    if (groups.length === 1) {
        if (!/^[0-9]+$/.test(groups[0])) { return null; }
    } else {
        for (var g = 0; g < groups.length; g++) {
            if (!/^[0-9]+$/.test(groups[g])) { return null; }
            if (g === 0) {
                if (groups[g].length < 1 || groups[g].length > 3) {
                    return null;
                }
            } else if (groups[g].length !== 3) {
                return null;
            }
        }
    }
    var num = parseFloat(groups.join('') + (fracpart === '' ? '' : '.' + fracpart));
    if (isNaN(num)) { return null; }
    return negative ? -num : num;
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
