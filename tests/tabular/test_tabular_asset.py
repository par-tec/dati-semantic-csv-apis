import os

import pytest
import yaml
from deepdiff import DeepDiff

from tests.constants import ASSETS
from tools.tabular import Tabular


@pytest.mark.asset
@pytest.mark.parametrize(
    "vocabulary_ttl",
    argvalues=ASSETS.glob("**/*.ttl"),
    ids=[x.name for x in ASSETS.glob("**/*.ttl")],
)
def test_tabular_metadata(
    vocabulary_ttl, snapshot, request: pytest.FixtureRequest
):
    """
    Test the metadata extraction from RDF data and creation of a datapackage descriptor.

    Given:
    - RDF vocabulary data in Turtle format
    - A JSON-LD frame with @context definitions

    When:
    - I create an instance of the Tabular class with the RDF data and frame
    - I call the metadata method to extract metadata and create a datapackage descriptor

    Then:
    - The metadata method should return a valid datapackage descriptor dictionary
    """
    datapackage_yaml = snapshot / request.node.name / "datapackage.yaml"

    tabular = Tabular(
        rdf_data=vocabulary_ttl, frame={"@context": {}}
    )  # Placeholder frame, replace with actual frame if needed
    vocab = tabular.datapackage_stub()

    if os.environ.get("UPDATE_SNAPSHOTS", "false").lower() == "true":
        datapackage_yaml.parent.mkdir(parents=True, exist_ok=True)
        datapackage_yaml.write_text(yaml.safe_dump(vocab))
        raise pytest.fail("Snapshot updated, skipping test.")

    assert datapackage_yaml.exists()

    diff = DeepDiff(vocab, yaml.safe_load(datapackage_yaml.read_text()))
    assert not diff, "Metadata extraction does not match expected snapshot"
