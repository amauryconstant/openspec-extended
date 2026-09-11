#!/usr/bin/env python3
# ruff: noqa: EXE001 - shebang is intentional for `python -m source`
"""
OpenSpec-extended - Entry point for python -m source
"""

from source.cli import app

if __name__ == "__main__":
    app()
