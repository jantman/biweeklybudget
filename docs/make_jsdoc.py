#!/usr/bin/env python
"""
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
"""

import sys
import os
import re
from sphinx_js.jsdoc import jsdoc_output, Analyzer
from sphinx_js.renderers import AutoFunctionRenderer
from collections import defaultdict

index_head = """UI JavaScript Docs
==================

Files
-----

.. toctree::

"""


class JSDocumenter(object):
    """
    Generate .rst files for javascript documentation. The ``sphinx-jsdoc``
    package does this nicely, but requires ``jsdoc`` to be available at
    build time, which rules out readthedocs.org. So... we hack apart that
    package to get it to generate static rST files on-demand, which we then save
    in the source directory.
    """

    func_re = re.compile(r'^function ([^\(]+)\([^\)]*\) {')

    def __init__(self, toxinidir):
        """
        Initialize class

        :param toxinidir: tox.ini directory
        :type toxinidir: str
        """
        self.toxinidir = toxinidir
        self.jsdir = os.path.join(
            toxinidir, 'biweeklybudget', 'flaskapp', 'static', 'js'
        )
        self.srcdir = os.path.join(
            toxinidir, 'docs', 'source'
        )
        self.app = FakeApp()
        self.app.config.js_source_path = self.jsdir
        self.app.confdir = self.srcdir

    def run(self):
        """
        Main entry point to build jsdoc
        """
        self._cleanup()
        # Use new jsdoc_output API instead of run_jsdoc
        doclets = jsdoc_output(
            None,           # cache
            [self.jsdir],   # abs_source_paths
            self.toxinidir, # base_dir
            self.srcdir,    # sphinx_conf_dir
            None            # config_path
        )

        # Create an Analyzer instance from the doclets for IR conversion
        self.analyzer = Analyzer(doclets, self.toxinidir)

        # Build doclets_by_longname dict from the list of doclets
        self.doclets_by_longname = {}
        for doclet in doclets:
            if 'longname' in doclet:
                self.doclets_by_longname[doclet['longname']] = doclet

        # build a dict of files to the list of function longnames in them
        funcs_per_file = defaultdict(type([]))
        for longname in self.doclets_by_longname.keys():
            d = self.doclets_by_longname[longname]
            if d.get('kind') not in ['function', 'class']:
                continue
            if 'meta' not in d or 'filename' not in d['meta']:
                continue
            funcs_per_file[d['meta']['filename']].append(longname)
        index = index_head
        for fname in sorted(funcs_per_file.keys()):
            refname = self._docs_for_file(fname, funcs_per_file[fname])
            index += "   %s\n" % refname
        with open(os.path.join(self.srcdir, 'jsdoc.rst'), 'w') as fh:
            fh.write(index)
        print('Wrote: jsdoc.rst')

    def _docs_for_file(self, fname, func_longnames):
        """
        Generate and write documentation for a given JS file. Return the
        sphinx reference name for the file.

        :param fname: name of the file
        :type fname: str
        :param func_longnames: list of function longnames to document
        :type func_longnames: list
        :return: sphinx reference name for file
        :rtype: str
        """
        print("Documenting %s" % fname)
        shortname = fname.split('.')[0]
        refname = 'jsdoc.%s' % shortname
        refname_esc = refname.replace('_', r'\_')
        doclet = self.doclets_by_longname[func_longnames[0]]
        path = os.path.join(doclet['meta']['path'], fname)
        body = "%s\n" % refname_esc
        body += ('=' * len(refname_esc)) + "\n\n"
        body += "File: ``%s``\n\n" % path.replace(
            os.path.realpath(self.toxinidir) + '/', ''
        )
        for funcname in sorted(func_longnames):
            r = AutoFunctionRenderer(FakeDirective(), self.app, arguments=[funcname])
            doclet = self.doclets_by_longname.get(funcname)
            # Determine the type (function or class) and get the IR object
            doc_type = 'class' if doclet.get('kind') == 'class' else 'function'
            try:
                ir_obj = self.analyzer.get_object(funcname.split('.'), doc_type)
                body += r.rst(funcname, ir_obj)
            except Exception as e:
                print(f"\tWarning: Could not render {funcname}: {e}")
        docpath = os.path.join(self.srcdir, '%s.rst' % refname)
        with open(docpath, 'w') as fh:
            fh.write(body)
        print("\tWritten to: %s" % docpath)
        return refname

    def _cleanup(self):
        """
        Remove existing jsdoc source files.
        """
        print('Cleaning up existing jsdoc*.rst source files...')
        for f in os.listdir(self.srcdir):
            p = os.path.join(self.srcdir, f)
            if not os.path.isfile(p):
                continue
            if not f.startswith('jsdoc') or not f.endswith('.rst'):
                continue
            print("\t%s" % p)
            os.unlink(p)


class Settings(object):
    tab_width = 8


class Document(object):
    settings = Settings()


class State(object):
    document = Document()


class FakeDirective(object):
    state = State()


class Config(object):
    jsdoc_config_path = None
    js_source_path = None
    jsdoc_cache = None
    ts_type_xref_formatter = None


class FakeApp(object):
    config = Config()
    confdir = None
    _sphinxjs_doclets_by_class = None
    _sphinxjs_doclets_by_longname = None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: make_jsdoc.py TOXINIDIR")
        raise SystemExit(1)
    JSDocumenter(sys.argv[1]).run()
