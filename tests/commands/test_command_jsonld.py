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
            "ttl": TESTDATA / "currency.ttl",
            "frame": TESTDATA / "currency.frame.yamlld",
            "uri": "http://publications.europa.eu/resource/authority/currency",
            "batch_size": "0",
            "expected_items": 179,
            "snapshot_file": "currency.data.yamlld",
        },
        marks=pytest.mark.slow,
        id="currency",
    ),
    pytest.param(
        "ateco-2025",
        {
            "ttl": ASSETS / "ateco-2025" / "ateco-2025.ttl",
            "frame": ASSETS / "ateco-2025" / "ateco-2025.frame.yamlld",
            "uri": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
            "batch_size": "1000",
            "expected_items": 3257,
        },
        marks=pytest.mark.asset,
        id="ateco-2025",
    ),
]

JSONLD_VALIDATE_FIXTURES = [
    pytest.param(
        "currency",
        {
            "ttl": TESTDATA / "currency.ttl",
            "uri": "http://publications.europa.eu/resource/authority/currency",
            "snapshot_file": "currency.data.yamlld",
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

    result = runner.invoke(
        cli,
        [
            "jsonld",
            "create",
            "--ttl",
            str(params["ttl"]),
            "--frame",
            str(params["frame"]),
            "--vocabulary-uri",
            params["uri"],
            "--output",
            str(output),
            "--frame-only",
            "--batch-size",
            params["batch_size"],
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()

    with output.open(encoding="utf-8") as f:
        framed = yaml.safe_load(f)
        assert "@graph" in framed, "Output JSON-LD must contain '@graph'"
        actual_items = len(framed["@graph"])
        assert actual_items == params["expected_items"], (
            f"Expected {params['expected_items']} items, found {actual_items}"
        )

    # Check against snapshot if available
    if "snapshot_file" in params:
        snapshot_path = snapshot.joinpath(params["snapshot_file"])
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
    jsonld_file = snapshot.joinpath(params["snapshot_file"])

    result = runner.invoke(
        cli,
        [
            "jsonld",
            "validate",
            "--ttl",
            str(params["ttl"]),
            "--vocabulary-uri",
            params["uri"],
            "--jsonld",
            str(jsonld_file),
        ],
    )

    assert result.exit_code == 0, result.output
