"""
Parameterized tests for jsonld create and validate commands.

Tests are organized by vocabulary and command type with shared test parameters.
"""

from pathlib import Path

import pytest
import yaml

from tests.constants import TESTDIR
from tools.commands import cli

_TESTCASES_YAML = Path(__file__).with_suffix(".yaml")
_TESTCASES = yaml.safe_load(_TESTCASES_YAML.read_text())


def _resolve_arg(arg: str) -> str | Path:
    """Resolve path-like args relative to TESTDIR; leave flags and URIs as-is."""
    if arg.startswith("-") or arg.startswith("http") or "/" not in arg:
        return arg
    candidate = (TESTDIR / arg).resolve()
    return candidate if candidate.exists() else arg


def _build_args(command: list[str]) -> list[str | Path]:
    return [_resolve_arg(a) for a in command]


def _make_fixtures() -> list:
    by_vocab: dict[str, dict] = {}
    for tc in _TESTCASES:
        tc_id: str = tc["id"]
        if tc_id.startswith("create_"):
            vocab_name = tc_id[len("create_") :]
            by_vocab.setdefault(vocab_name, {})["create"] = tc
        elif tc_id.startswith("validate_"):
            vocab_name = tc_id[len("validate_") :]
            by_vocab.setdefault(vocab_name, {})["validate"] = tc

    fixtures = []
    for vocab_name, steps in by_vocab.items():
        create_tc = steps.get("create")
        validate_tc = steps.get("validate")
        marks = []
        params: dict = {}
        if create_tc:
            step = create_tc["steps"][0]
            marks = [
                getattr(pytest.mark, m) for m in create_tc.get("marks", [])
            ]
            params["create_args"] = _build_args(step["command"])
            params["expected_logs"] = step["expected"].get("logs", [])
        if validate_tc:
            step = validate_tc["steps"][0]
            if not marks:
                marks = [
                    getattr(pytest.mark, m)
                    for m in validate_tc.get("marks", [])
                ]
            params["validate_args"] = _build_args(step["command"])
        fixtures.append(
            pytest.param(vocab_name, params, marks=marks, id=vocab_name)
        )
    return fixtures


JSONLD_FIXTURES = _make_fixtures()


@pytest.mark.parametrize("vocab_name,params", JSONLD_FIXTURES)
def test_jsonld(vocab_name, params, tmp_path, runner, snapshot, caplog):
    """
    Execute the test suite defined in the associated YAML file.
    """
    output = tmp_path / f"{vocab_name}.data.yamlld"

    if create_args := params.get("create_args"):
        result = runner.invoke(cli, [*create_args, "--output", str(output)])
        assert result.exit_code == 0, result.output
        assert output.exists()

        with output.open(encoding="utf-8") as f:
            framed = yaml.safe_load(f)
        assert "@graph" in framed, "Output JSON-LD must contain '@graph'"

        for log in params["expected_logs"]:
            assert log in caplog.text, f"Expected log message not found: {log}"

        snapshot_path = snapshot.joinpath(f"{vocab_name}.data.yamlld")
        if snapshot_path.exists():
            assert snapshot_path.read_bytes() == output.read_bytes()

    if validate_args := params.get("validate_args"):
        # Use freshly created output when available, otherwise fall back to snapshot.
        if not output.exists():
            output = snapshot.joinpath(vocab_name).with_suffix(".data.yamlld")
        assert output.exists(), f"JSON-LD file not found: {output}"
        result = runner.invoke(cli, [*validate_args, "--jsonld", str(output)])
        assert result.exit_code == 0, result.output
