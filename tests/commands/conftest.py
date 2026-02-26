import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """
    Returns a CliRunner instance
    with catch_exceptions set to False for better debugging during tests.
    """
    return CliRunner(
        catch_exceptions=False,
    )
