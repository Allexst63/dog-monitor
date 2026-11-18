#!/usr/bin/env python3
"""Runs a script from the closed part of DOG Monitor (dog-monitor/engine) inside a public GitHub Actions run.

    python3 tools/quiet.py <script.py> [args...]

Logs of a public repository are public, and a normal Python error prints the source lines around the failure.
Here an error is reported as one line — the error type, its message and line numbers — never the code itself.
Warnings are switched off for the same reason. Ordinary output of the script (its print lines) goes through as is.
"""
import os
import runpy
import sys
import traceback
import warnings

if len(sys.argv) < 2:
    sys.exit('usage: python3 tools/quiet.py <script.py> [args...]')
warnings.simplefilter('ignore')
path = os.path.abspath(sys.argv[1])
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(path))
sys.dont_write_bytecode = True
try:
    runpy.run_path(path, run_name='__main__')
except SystemExit as e:
    code = e.code
    if isinstance(code, str):
        print(code, file=sys.stderr)
        sys.exit(1)
    sys.exit(code or 0)
except BaseException as e:  # noqa: BLE001 — one line, no source
    tb = traceback.extract_tb(e.__traceback__)
    where = ', '.join(f'{os.path.basename(f.filename)}:{f.lineno}' for f in tb[-4:])
    print(f'ошибка: {type(e).__name__}: {str(e)[:300]} ({where})', file=sys.stderr)
    sys.exit(1)
