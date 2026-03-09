from pathlib import Path

import pytest

from tests.constants import DATADIR


@pytest.fixture
def snapshot() -> Path:
    """
    Returns a snapshot fixture for snapshot testing.
    """
    return DATADIR / "snapshots"


@pytest.fixture
def snapshot_dir(snapshot: Path, request: pytest.FixtureRequest) -> Path:
    """
    Returns a directory for the current test function to store snapshot files.

    The directory is created under the main snapshot directory, with a subdirectory named after the test function.
    """
    destdir = snapshot / request.node.name
    destdir.mkdir(parents=True, exist_ok=True)
    yield destdir
    # Eventually add cleanup code.
