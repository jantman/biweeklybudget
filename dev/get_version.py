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


ver = get_version()
print(f'App version: {ver}')
print(f'::set-output name=APP_VERSION::{ver}')
