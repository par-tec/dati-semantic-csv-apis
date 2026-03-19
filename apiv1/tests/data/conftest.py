from pathlib import Path

import pytest


@pytest.fixture
def sample_db():
    return (Path(__file__).parent.parent / "harvest.db").as_posix()
