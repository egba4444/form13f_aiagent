"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def fixtures_dir():
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def data_dir(project_root):
    """Return the data directory."""
    return project_root / "data"
