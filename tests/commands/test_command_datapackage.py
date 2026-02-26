"""
Parameterized tests for datapackage create and validate commands.

Tests are organized by vocabulary and command type with shared test parameters.
"""

import logging

import pytest
from click.testing import CliRunner

from tests.commands.utils import harness_step, make_fixtures

DATAPACKAGE_FIXTURES = make_fixtures(__file__)


@pytest.mark.parametrize("params", argvalues=DATAPACKAGE_FIXTURES)
def test_datapackage(
    params, runner: CliRunner, caplog: pytest.LogCaptureFixture
):
    """
    Execute the test suite defined in the associated YAML file.
    """
    # Set DEBUG log level for this specific test,
    #   so we can test log messages.
    caplog.set_level(logging.DEBUG)

    for step in params["steps"]:
        harness_step(step, runner, caplog)
