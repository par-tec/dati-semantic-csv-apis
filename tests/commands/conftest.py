from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.constants import DATADIR


@pytest.fixture
def runner():
    """
    Returns a CliRunner instance
    with catch_exceptions set to False for better debugging during tests.
    """
    return CliRunner(
        catch_exceptions=False,
    )


@pytest.fixture
def snapshot() -> Path:
    """
    Returns a snapshot fixture for snapshot testing.
    """
    return DATADIR / "snapshots"
