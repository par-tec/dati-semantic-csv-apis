from pathlib import Path

import pytest


@pytest.fixture
def TESTDIR():
    return Path(__file__).parent


@pytest.fixture
def DATADIR(TESTDIR):
    return TESTDIR / "data"
