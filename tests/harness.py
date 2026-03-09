from pathlib import Path

import yaml
from deepdiff import DeepDiff
from git import Repo

from tests.constants import TESTDIR


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


def compare_data(snapshot_file: Path, current_file: Path):
    """
    Compare the data content of two files,
    eventually retrieving the last committed version
    from git.
    """
    current_data = yaml.safe_load(current_file.read_text())

    if snapshot_file == current_file:
        snapshot_raw: str = git_show_head(current_file)
        snapshot_data = yaml.safe_load(snapshot_raw)
    else:
        snapshot_data = yaml.safe_load(snapshot_file.read_text())

    delta = DeepDiff(snapshot_data, current_data, ignore_order=True)

    assert not delta, (
        f"File {current_file} differs from {snapshot_file}."
        f" Either {current_file} is wrong,"
        f" or {snapshot_file} has uncommitted changes."
        f"\ndiff:\n{delta}"  # limit diff output to 500 chars
    )


def compare_content(snapshot_file: Path, current_file: Path):
    if snapshot_file == current_file:
        # compare the current_file to its git commited version.
        delta = git_diff(snapshot_file)
        assert not delta, (
            f"File {snapshot_file} has uncommitted changes. Please commit the file or update the snapshot reference."
            f"\nGit diff:\n{delta.decode('utf-8')[:500]}"  # limit diff output to 500 chars
        )
    else:
        assert snapshot_file.exists(), (
            f"Expected snapshot file not found: {snapshot_file}"
        )
        assert snapshot_file.read_bytes() == current_file.read_bytes()


def git_show_head(path: Path) -> str:
    """
    Get the git show of a file at HEAD as bytes.

    :param path: Path to the file to get the show for
    :return: The git show as bytes
    """
    repo = Repo(TESTDIR.parent, search_parent_directories=True)
    relative_path = path.relative_to(TESTDIR.parent)
    show = repo.git.show(
        f"HEAD:{relative_path.as_posix()}",
    )
    return show


def git_diff(path: Path) -> bytes:
    """
    Get the git diff of a file as bytes.

    :param path: Path to the file to get the diff for
    :return: The git diff as bytes
    """

    repo = Repo(TESTDIR.parent, search_parent_directories=True)
    diff = repo.git.diff("HEAD", path.as_posix(), ignore_cr_at_eol=True)
    return diff.encode("utf-8")
