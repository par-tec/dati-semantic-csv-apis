from pathlib import Path

import pytest

from tests.constants import DATADIR


@pytest.fixture
def snapshot() -> Path:
    """
    Returns a snapshot fixture for snapshot testing.
    """
    return DATADIR / "snapshots"
