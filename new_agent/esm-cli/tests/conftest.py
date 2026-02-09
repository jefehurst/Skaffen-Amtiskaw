"""Pytest fixtures for ESM tests."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "v24"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to v24 fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def load_fixture():
    """Factory fixture to load HTML fixtures as BeautifulSoup."""

    def _load(name: str) -> BeautifulSoup:
        path = FIXTURES_DIR / name
        with open(path) as f:
            return BeautifulSoup(f.read(), "lxml")

    return _load


@pytest.fixture
def environments_html(load_fixture):
    """Load environments list HTML."""
    return load_fixture("environments.html")


@pytest.fixture
def products_html(load_fixture):
    """Load products list HTML."""
    return load_fixture("products.html")


@pytest.fixture
def available_releases_html(load_fixture):
    """Load available releases HTML."""
    return load_fixture("available-releases.html")


@pytest.fixture
def upgrade_properties_html(load_fixture):
    """Load upgrade properties HTML."""
    return load_fixture("upgrade-properties.html")


@pytest.fixture
def job_in_progress_html(load_fixture):
    """Load job in progress HTML."""
    return load_fixture("job-in-progress.html")


@pytest.fixture
def job_completed_html(load_fixture):
    """Load job completed HTML."""
    return load_fixture("job-completed.html")
