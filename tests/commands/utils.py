from pathlib import Path

import pytest
import yaml


def make_fixtures(testfile) -> list:
    """
    Pre-process the per-testfile testcases to create a list of fixtures for parameterized testing.

    :warning: This is specific to this folder.
    """
    _testcases_yaml = Path(testfile).with_suffix(".yaml")
    _testcases = yaml.safe_load(_testcases_yaml.read_text())

    fixtures = []
    for tc in _testcases:
        params: dict = {}
        params["steps"] = tc["steps"]
        marks = [getattr(pytest.mark, m) for m in tc.get("marks", [])]
        fixtures.append(pytest.param(params, marks=marks, id=tc["id"]))
    return fixtures


def assert_file(fileinfo: dict):
    path = Path(fileinfo["path"])
    assert path.exists() == fileinfo.get("exists", True), (
        f"Expected file not found: {path}"
    )

    if snapshot_path := fileinfo.get("snapshot"):
        snapshot_file: Path = Path(snapshot_path)
        assert snapshot_file.exists(), (
            f"Expected snapshot file not found: {snapshot_file}"
        )
        assert snapshot_file.read_bytes() == path.read_bytes()
