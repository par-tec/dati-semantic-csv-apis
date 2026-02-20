"""
Parameterized tests for jsonld create and validate commands.

Tests are organized by vocabulary and command type with shared test parameters.
"""

from pathlib import Path

import pytest
import yaml

from tools.commands import cli

TESTDIR = Path(__file__).parent.parent
TESTDATA = TESTDIR / "data"
ASSETS = TESTDIR.parent / "assets" / "controlled-vocabularies"


# Test fixtures shared across parameterized tests
JSONLD_CREATE_FIXTURES = [
    pytest.param(
        "currency",
        {
            "args": [
                "jsonld",
                "create",
                "--ttl",
                TESTDATA / "currency.ttl",
                "--frame",
                TESTDATA / "currency.frame.yamlld",
                "--vocabulary-uri",
                "http://publications.europa.eu/resource/authority/currency",
                "--batch-size",
                "0",
                "--frame-only",
            ],
            "expected": {
                "expected_items": 179,
            },
        },
        marks=pytest.mark.slow,
        id="currency",
    ),
    pytest.param(
        "ateco-2025",
        {
            "args": [
                "jsonld",
                "create",
                "--ttl",
                ASSETS / "ateco-2025" / "ateco-2025.ttl",
                "--frame",
                ASSETS / "ateco-2025" / "ateco-2025.frame.yamlld",
                "--vocabulary-uri",
                "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
                "--batch-size",
                "1000",
                "--frame-only",
            ],
            "expected": {
                "expected_items": 3257,
            },
        },
        marks=pytest.mark.asset,
        id="ateco-2025",
    ),
]

JSONLD_VALIDATE_FIXTURES = [
    pytest.param(
        "currency",
        {
            "args": [
                "jsonld",
                "validate",
                "--ttl",
                TESTDATA / "currency.ttl",
                "--vocabulary-uri",
                "http://publications.europa.eu/resource/authority/currency",
            ],
        },
        marks=pytest.mark.slow,
        id="currency",
    ),
]


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
