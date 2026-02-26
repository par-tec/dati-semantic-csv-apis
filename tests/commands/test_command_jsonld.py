"""
Parameterized tests for jsonld create and validate commands.

Tests are organized by vocabulary and command type with shared test parameters.
"""

import logging

import pytest

from tests.commands.utils import assert_file, make_fixtures
from tools.commands import cli

JSONLD_FIXTURES = make_fixtures(__file__)


@pytest.mark.parametrize("vocab_name,params", JSONLD_FIXTURES)
def test_jsonld(vocab_name, params, tmp_path, runner, snapshot, caplog):
    """
    Execute the test suite defined in the associated YAML file.
    """
    # Set DEBUG log level for this specific test,
    #   so we can test log messages.
    caplog.set_level(logging.DEBUG)

    expected = params["expected"]

    # When I execute the command ...
    args = params.get("args")
    result = runner.invoke(cli, args)

    # Then the status code is as expected...
    assert result.exit_code == expected.get("exit_status", 0), result.output

    # ... the output ...
    for out in expected.get("stdout", []):
        assert out in result.output, f"Expected stdout message not found: {out}"

    # ... the logs ...
    for log in expected.get("logs", []):
        assert log in caplog.text, f"Expected log message not found: {log}"

    # If there's an expected output file, it should match the snapshot
    for fileinfo in expected.get("files", []):
        assert_file(fileinfo)
