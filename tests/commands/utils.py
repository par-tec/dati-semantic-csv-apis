import logging
import re
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from deepdiff import DeepDiff
from git import Repo

from tests.constants import TESTDIR
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
    for out in expected.get("stdout", []):
        assert re.findall(out, result.output), (
            f"Expected stdout message not found: {out}"
        )

    # ... the logs ...
    for log in expected.get("logs", []):
        assert re.findall(log, caplog.text), (
            f"Expected log message not found: {log}"
        )

    # If there's an expected output file, it should match the snapshot
    for fileinfo in expected.get("files", []):
        assert_file(fileinfo)


def assert_file(fileinfo: dict):
    path = Path(fileinfo["path"])
    assert path.exists() == fileinfo.get("exists", True), (
        f"Expected file not found: {path}"
    )

    assert_snapshot(fileinfo)


def assert_snapshot(fileinfo: dict):
    snapshot_path = fileinfo.get("snapshot")
    if not snapshot_path:
        return
    path = Path(fileinfo["path"])
    snapshot_file: Path = Path(snapshot_path)

    match fileinfo.get("compare"):
        case "data":
            compare_f = compare_data
        case _:
            compare_f = compare_content

    compare_f(snapshot_file, path)


def compare_data(snapshot_file: Path, path: Path):
    snapshot_data = yaml.safe_load(snapshot_file.read_text())
    path_data = yaml.safe_load(path.read_text())
    delta = DeepDiff(snapshot_data, path_data, ignore_order=True)
    assert delta == {}


def compare_content(snapshot_file: Path, path: Path):
    if snapshot_file == path:
        # compare the path file to its git commited version.
        delta = git_diff(path)
        assert not delta, (
            f"File {path} has uncommitted changes. Please commit the file or update the snapshot reference."
            f"\nGit diff:\n{delta.decode('utf-8')[:500]}"  # limit diff output to 500 chars
        )
    else:
        assert snapshot_file.exists(), (
            f"Expected snapshot file not found: {snapshot_file}"
        )
        assert snapshot_file.read_bytes() == path.read_bytes()


def git_diff(path: Path) -> bytes:
    """
    Get the git diff of a file as bytes.

    :param path: Path to the file to get the diff for
    :return: The git diff as bytes
    """

    repo = Repo(TESTDIR.parent, search_parent_directories=True)
    diff = repo.git.diff("HEAD", path.as_posix(), ignore_cr_at_eol=True)
    return diff.encode("utf-8")
