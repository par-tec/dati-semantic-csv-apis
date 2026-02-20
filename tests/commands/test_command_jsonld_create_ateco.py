from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from tools.commands import cli

ASSET = (
    Path(__file__).parent.parent.parent / "assets" / "controlled-vocabularies"
)
ATECO_2025 = ASSET / "ateco-2025"
ATECO_2025_TTL = ATECO_2025 / "ateco-2025.ttl"
ATECO_2025_URI = (
    "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025"
)


@pytest.mark.asset
def test_frame_command_ateco_2025(tmp_path):
    """
    Given:
    - The ateco-2025 RDF vocabulary file
    - A JSON-LD frame file

    When:
    - I run the `jsonld create` command

    Then:
    - The command exits successfully
    - The output JSON-LD framed file is created
    """
    output = tmp_path / "ateco-2025.jsonld"
    frame = ATECO_2025 / "ateco-2025.frame.yamlld"

    runner = CliRunner(catch_exceptions=False)
    result = runner.invoke(
        cli,
        [
            "jsonld",
            "create",
            "--ttl",
            str(ATECO_2025_TTL),
            "--frame",
            str(frame),
            "--vocabulary-uri",
            ATECO_2025_URI,
            "--output",
            str(output),
            "--batch-size",
            "1000",
            "--frame-only",
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()
    expected_items = 3257
    with output.open(encoding="utf-8") as f:
        framed = yaml.safe_load(
            f
        )  # Validate that the output is valid YAML/JSON
        assert "@graph" in framed, "Output JSON-LD must contain '@graph'"
        assert len(framed["@graph"]) == expected_items, (
            f"Expected {expected_items} items in the framed output, found {len(framed['@graph'])}"
        )
    return
