#!/usr/bin/env python

import sys
import os
import re

index_head = """UI JavaScript Docs
==================

Files
-----

.. toctree::

"""

class JSDocumenter(object):
    """
    Generate .rst files for javascript documentation.
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

    def run(self):
        """
        Main entry point to build jsdoc
        """
        self._cleanup()
        jsfiles = self._find_js_files()
        index = index_head
        for fname in sorted(jsfiles.keys()):
            refname = self._docs_for_file(fname, jsfiles[fname])
            index += "   %s\n" % refname
        with open(os.path.join(self.srcdir, 'jsdoc.rst'), 'w') as fh:
            fh.write(index)
        print('Wrote: jsdoc.rst')

    def _docs_for_file(self, fname, path):
        """
        Generate and write documentation for a given JS file. Return the
        sphinx reference name for the file.

        :param fname: name of the file
        :type fname: str
        :param path: full path to the file
        :type path: str
        :return: sphinx reference name for file
        :rtype: str
        """
        print("Documenting %s" % fname)
        shortname = fname.split('.')[0]
        refname = 'jsdoc.%s' % shortname
        refname_esc = refname.replace('_', '\_')
        body = "%s\n" % refname_esc
        body += ('=' * len(refname_esc)) + "\n\n"
        body += "File: ``%s``\n\n" % path.replace(self.toxinidir, '')
        for d in self._directives_for_file(path):
            body += "%s\n\n" % d
        docpath = os.path.join(self.srcdir, '%s.rst' % refname)
        with open(docpath, 'w') as fh:
            fh.write(body)
        print("\tWritten to: %s" % docpath)
        return refname

    def _directives_for_file(self, fpath):
        """
        Return a list of Sphinx rST directives for all document-able items
        in the specified JS file.

        :param fpath: path to the file
        :type fpath: str
        :return: sphinx directives for the file
        :rtype: list
        """
        res = []
        with open(fpath, 'r') as fh:
            for line in fh.readlines():
                line = line.strip()
                m = self.func_re.match(line)
                if m:
                    res.append('.. js:autofunction:: %s' % m.group(1))
        return res

    def _find_js_files(self):
        """
        Return a dict of JS files, filename to full path.

        :return: dict of JS files
        :rtype: dict
        """
        files = {}
        for f in os.listdir(self.jsdir):
            p = os.path.join(self.jsdir, f)
            if not os.path.isfile(p):
                continue
            if f.endswith('.js'):
                files[f] = p
        return files

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

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: make_jsdoc.py TOXINIDIR")
        raise SystemExit(1)
    JSDocumenter(sys.argv[1]).run()
