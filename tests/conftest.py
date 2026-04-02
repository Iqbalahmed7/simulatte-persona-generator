"""tests/conftest.py — Test-level pytest configuration.

Registers the 'live' marker used by test_live_e2e.py.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="Run live API tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "live: mark test as requiring live API access")
