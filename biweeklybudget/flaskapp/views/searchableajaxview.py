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

from flask.views import MethodView


class SearchableAjaxView(MethodView):
    """
    MethodView with helper methods for searching via DataTables ajax.
    """

    def _args_dict(self, args):
        """
        Given a 1-dimensional dict of request parameters like those used by
        DataTables (i.e. keys like ``columns[2][search][value]``), return a
        multidimensional dict representation of the same.

        :return: deep/nested dict
        :rtype: dict
        """
        d = {}
        for k, v in args.items():
            v = self._args_set_type(v)
            if '[' not in k:
                d[self._args_set_type(k)] = v
                continue
            k = k.replace('[', '|').replace(']', '|').replace('||', '|')
            k = k.strip('|')
            parts = k.split('|')
            ptr = d
            while len(parts) > 1:
                subk = self._args_set_type(parts.pop(0))
                if subk not in ptr:
                    ptr[subk] = {}
                ptr = ptr[subk]
            ptr[self._args_set_type(parts[0])] = v
        return d

    def _args_set_type(self, a):
        """
        Given a string portion of something in the argument dict, return it
        as the correct type.

        :param a: args dict key or value
        :type a: str
        :return: a in the proper type
        """
        try:
            if '%d' % int(a) == a:
                return int(a)
        except Exception:
            pass
        if a == 'true':
            return True
        if a == 'false':
            return False
        return a

    def _filterhack(self, qs, s, args):
        """
        DataTables 1.10.12 has built-in support for filtering based on a value
        in a specific column; when this is done, the filter value is set in
        ``columns[N][search][value]`` where N is the column number. However,
        the python datatables package used here only supports the global
        ``search[value]`` input, not the per-column one.

        However, the DataTable search is implemented by passing a callable
        to ``table.searchable()`` which takes two arguments, the current Query
        that's being built, and the user's ``search[value]`` input; this must
        then return a Query object with the search applied.

        In python datatables 0.4.9, this code path is triggered on
        ``if callable(self.search_func) and search.get("value", None):``

        As such, we can "trick" the table to use per-column searching (currently
        only if global searching is not being used) by examining the per-column
        search values in the request, and setting the search function to one
        (this method) that uses those values instead of the global
        ``search[value]``.

        :param qs: Query currently being built
        :type qs: ``sqlalchemy.orm.query.Query``
        :param s: user search value
        :type s: str
        :param args: args
        :type args: dict
        :return: Query with searching applied
        :rtype: ``sqlalchemy.orm.query.Query``
        """
        raise NotImplementedError()

    def _have_column_search(self, args):
        """
        Determine if we have a column filter/search in effect, and if so,
        should use :py:meth:`~._filterhack` as our search function.

        :param args: current request arguments
        :type args: dict
        :return: whether or not request asks for column filtering
        :rtype: bool
        """
        for col in args['columns']:
            if args['columns'][col]['search']['value'] != '':
                return True
        return False

    def get(self):
        """
        Render and return JSON response for GET.
        """
        raise NotImplementedError()
