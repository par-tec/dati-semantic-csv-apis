from pathlib import Path

import pytest

TESTDIR = Path(__file__).parent.parent
DATADIR = TESTDIR / "data"


@pytest.fixture
def sample_db():
    return (DATADIR / "aggregate.db").as_posix()
