import logging
import re
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from tests.harness import assert_file
from tools.commands import cli


def make_fixtures(testfile) -> list:
    """
    Pre-process the per-testfile testcases to create a list of fixtures for parameterized testing.

    :warning: This is specific to this folder.
    """
    _testcases_yaml = Path(testfile).with_suffix(".yaml")
    _testcases = yaml.safe_load(_testcases_yaml.read_text())

    fixtures = []
    for tc in _testcases:
        if tc.get("skip", False):
            logging.warning(f"Skipping test case: {tc['id']}")
            continue
        params: dict = {}
        params["steps"] = tc["steps"]
        marks = [getattr(pytest.mark, m) for m in tc.get("marks", [])]
        fixtures.append(pytest.param(params, marks=marks, id=tc["id"]))
    return fixtures


def harness_step(step, runner: CliRunner, caplog: pytest.LogCaptureFixture):
    if step.get("skip", False):
        logging.warning(
            f"Skipping step: {step.get('description', 'No description')}"
        )
        return

    expected = step["expected"]

    # When I execute the command ...
    result = runner.invoke(cli, step["command"])

    # Then the status code is as expected...
    assert result.exit_code == expected.get("exit_status", 0), result.output

    # ... the output ...
    for expected_stdout in expected.get("stdout", []):
        assert re.findall(expected_stdout, result.output), (
            f"Expected stdout message not found: {expected_stdout}"
        )

    # ... the logs ...
    for expected_log in expected.get("logs", []):
        assert re.findall(expected_log, caplog.text), (
            f"Expected log message not found: {expected_log}"
        )

    # If there's an expected output file, it should match the snapshot
    for fileinfo in expected.get("files", []):
        assert_file(fileinfo)
