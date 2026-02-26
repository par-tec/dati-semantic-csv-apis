"""
Parameterized tests for jsonld create and validate commands.

Tests are organized by vocabulary and command type with shared test parameters.
"""

from pathlib import Path

import pytest
import yaml

from tests.constants import TESTDIR
from tools.commands import cli

_TESTCASES_YAML = Path(__file__).parent / "test-command-jsonld.yaml"
_TESTCASES = yaml.safe_load(_TESTCASES_YAML.read_text())


def _resolve_arg(arg: str) -> str | Path:
    """Resolve path-like args relative to TESTDIR; leave flags and URIs as-is."""
    if arg.startswith("-") or arg.startswith("http") or "/" not in arg:
        return arg
    candidate = (TESTDIR / arg).resolve()
    return candidate if candidate.exists() else arg


def _build_args(command: list[str]) -> list[str | Path]:
    return [_resolve_arg(a) for a in command]


def _make_create_fixtures() -> list:
    fixtures = []
    for tc in _TESTCASES:
        if not tc["id"].startswith("create_"):
            continue
        vocab_name = tc["id"][len("create_") :]
        step = tc["steps"][0]
        marks = [getattr(pytest.mark, m) for m in tc.get("marks", [])]
        fixtures.append(
            pytest.param(
                vocab_name,
                {
                    "args": _build_args(step["command"]),
                    "expected": {"expected_items": step["expected"]["items"]},
                },
                marks=marks,
                id=vocab_name,
            )
        )
    return fixtures


def _make_validate_fixtures() -> list:
    fixtures = []
    for tc in _TESTCASES:
        if not tc["id"].startswith("validate_"):
            continue
        vocab_name = tc["id"][len("validate_") :]
        step = tc["steps"][0]
        marks = [getattr(pytest.mark, m) for m in tc.get("marks", [])]
        fixtures.append(
            pytest.param(
                vocab_name,
                {"args": _build_args(step["command"])},
                marks=marks,
                id=vocab_name,
            )
        )
    return fixtures


JSONLD_CREATE_FIXTURES = _make_create_fixtures()
JSONLD_VALIDATE_FIXTURES = _make_validate_fixtures()


@pytest.mark.parametrize("vocab_name,params", JSONLD_CREATE_FIXTURES)
def test_jsonld_create(vocab_name, params, tmp_path, runner, snapshot):
    """
    Test jsonld create command for various vocabularies.

    Given:
    - A vocabulary TTL file and JSON-LD frame

    When:
    - I run the `jsonld create` command

    Then:
    - The command exits successfully
    - The output JSON-LD framed file is created with expected items
    """
    output = tmp_path / f"{vocab_name}.data.yamlld"

    args = params["args"]
    result = runner.invoke(
        cli,
        args
        + [
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()

    with output.open(encoding="utf-8") as f:
        framed = yaml.safe_load(f)
        assert "@graph" in framed, "Output JSON-LD must contain '@graph'"

        expected = params["expected"]
        actual_items = len(framed["@graph"])
        assert actual_items == expected["expected_items"], (
            f"Expected {expected['expected_items']} items, found {actual_items}"
        )

    # Check against snapshot if available
    snapshot_path = snapshot.joinpath(f"{vocab_name}.data.yamlld")
    if snapshot_path.exists():
        assert snapshot_path.read_bytes() == output.read_bytes()


@pytest.mark.parametrize("vocab_name,params", JSONLD_VALIDATE_FIXTURES)
def test_jsonld_validate(vocab_name, params, runner, snapshot):
    """
    Test jsonld validate command for various vocabularies.

    Given:
    - A vocabulary TTL file and JSON-LD framed file

    When:
    - I run the `jsonld validate` command

    Then:
    - The command exits successfully
    - Validation passes
    """
    jsonld_file = snapshot.joinpath(vocab_name).with_suffix(".data.yamlld")
    assert jsonld_file.exists(), (
        f"Snapshot JSON-LD file not found: {jsonld_file}"
    )

    args = params["args"]
    result = runner.invoke(
        cli,
        [*args, "--jsonld", str(jsonld_file)],
    )

    assert result.exit_code == 0, result.output
