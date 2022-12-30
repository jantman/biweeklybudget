#!/usr/bin/env python
import os
import importlib.util

def get_version():
    spec = importlib.util.spec_from_file_location(
        "version",
        os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            'biweeklybudget',
            'version.py'
        ))
    )
    version = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version)
    return version.VERSION


def get_release_notes(version):
    buf = ''
    in_ver = False
    with open('CHANGES.md', 'r') as fh:
        for line in fh.readlines():
            if not in_ver and line.startswith('## %s ' % version):
                in_ver = True
            elif in_ver and line.startswith('## '):
                return buf
            elif in_ver:
                buf += line
        return buf


clog = get_release_notes(get_version())
print(clog)
with open('release_log.md', 'w') as fh:
    fh.write(clog)
