from pathlib import Path

import pytest
from click.testing import CliRunner

TESTDIR = Path(__file__).parent.parent
DATADIR = TESTDIR / "data"


@pytest.fixture
def runner():
    """
    Returns a CliRunner instance with catch_exceptions set to False for better debugging during tests.
    """
    return CliRunner(catch_exceptions=False)


@pytest.fixture
def snapshot() -> Path:
    """
    Returns a snapshot fixture for snapshot testing.
    """
    return DATADIR / "snapshots"
