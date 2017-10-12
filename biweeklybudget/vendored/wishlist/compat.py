# -*- coding: utf-8 -*-

import sys
import hashlib

# shamelessly ripped from https://github.com/kennethreitz/requests/blob/master/requests/compat.py
# Syntax sugar.
_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

if is_py2:
    from StringIO import StringIO

    basestring = basestring
    range = xrange # range is now always an iterator

    # http://stackoverflow.com/questions/14503751
    # ripped from six https://bitbucket.org/gutworth/six
    exec("""def reraise(tp, value, tb=None):
        try:
            raise tp, value, tb
        finally:
            tb = None
    """)

    # http://stackoverflow.com/a/5297483/5006
    def md5(text):
        return hashlib.md5(text).hexdigest()


elif is_py3:
    from io import StringIO

    basestring = (str, bytes)

    def md5(text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    # ripped from six https://bitbucket.org/gutworth/six
    def reraise(tp, value, tb=None):
        try:
            if value is None:
                value = tp()
            if value.__traceback__ is not tb:
                raise value.with_traceback(tb)
            raise value
        finally:
            value = None
            tb = None
