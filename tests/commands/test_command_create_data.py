from pathlib import Path

import pytest
import yaml

from tools.commands.create import cli as cli_create
from tools.commands.validate import cli as cli_validate

TESTDIR = Path(__file__).parent.parent
TESTDATA: Path = TESTDIR / "data"
CURRENCY_TTL = TESTDATA / "currency.ttl"
CURRENCY_FRAME = CURRENCY_TTL.with_suffix(".frame.yamlld")
CURRENCY_URI = "http://publications.europa.eu/resource/authority/currency"


@pytest.mark.slow
@pytest.mark.asset
def test_frame_command_currency(tmp_path, runner, snapshot):
    """
    Given:
    - The currency RDF vocabulary file
    - A JSON-LD frame file

    When:
    - I run the `framed` command

    Then:
    - The command exits successfully
    - The output JSON-LD framed file is created
    """
    output = tmp_path / "currency.data.yamlld"

    result = runner.invoke(
        cli_create,
        [
            "framed",
            "--ttl",
            str(CURRENCY_TTL),
            "--frame",
            str(CURRENCY_FRAME),
            "--vocabulary-uri",
            CURRENCY_URI,
            "--output",
            str(output),
            "--frame-only",
            "--batch-size",
            "0",
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()
    expected_items = 179
    with output.open(encoding="utf-8") as f:
        framed = yaml.safe_load(
            f
        )  # Validate that the output is valid YAML/JSON
        assert "@graph" in framed, "Output JSON-LD must contain '@graph'"
        actual_items = len(framed["@graph"])
        assert actual_items == expected_items, (
            f"Expected {expected_items} items in the framed output, found {actual_items}"
        )
    assert (
        snapshot.joinpath("currency.data.yamlld").read_bytes()
        == output.read_bytes()
    )


def test_validate_command_currency(tmp_path, runner, snapshot):
    """Given:
    - The currency RDF vocabulary file
    - A JSON-LD framed file created from the currency RDF vocabulary
    When:
    - I run the `validate jsonld` command to validate the framed JSON-LD against the original RDF vocabulary
    Then:
    - Success
    """
    output = snapshot / "currency.data.yamlld"
    result = runner.invoke(
        cli_validate,
        [
            "jsonld",
            "--ttl",
            str(CURRENCY_TTL),
            "--vocabulary-uri",
            CURRENCY_URI,
            "--jsonld",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
