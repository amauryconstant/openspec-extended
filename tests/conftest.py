#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for openspec-extended tests.
"""

import os
import pytest


def pytest_collection_modifyitems(config, items):
    """Skip e2e-marked tests unless E2E_CONFIRM=1.

    Mechanism tests are always collected and run; only tests marked
    purely as `e2e` are skipped.
    """
    if os.environ.get("E2E_CONFIRM") == "1":
        return
    skip_e2e = pytest.mark.skip(reason="Set E2E_CONFIRM=1 to run e2e tests")
    for item in items:
        keywords = item.keywords
        if "e2e" in keywords and "mechanism" not in keywords:
            item.add_marker(skip_e2e)
