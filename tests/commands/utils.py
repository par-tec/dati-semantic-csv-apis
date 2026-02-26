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
    by_vocab: dict[str, dict] = {}
    for tc in _testcases:
        tc_id: str = tc["id"]
        vocab_name = tc_id[len("create_") :]
        by_vocab.setdefault(vocab_name, {})["create"] = tc

    fixtures = []
    for vocab_name, steps in by_vocab.items():
        create_tc = steps.get("create")
        marks = []
        params: dict = {}
        step = create_tc["steps"][0]
        marks = [getattr(pytest.mark, m) for m in create_tc.get("marks", [])]
        params["args"] = step["command"]
        params["expected"] = step["expected"]
        if not marks:
            marks = [
                getattr(pytest.mark, m) for m in create_tc.get("marks", [])
            ]
        fixtures.append(
            pytest.param(vocab_name, params, marks=marks, id=vocab_name)
        )
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
