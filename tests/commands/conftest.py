import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """
    Returns a CliRunner instance
    """
    return CliRunner(
        catch_exceptions=False,
    )
