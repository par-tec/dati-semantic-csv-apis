from operator import itemgetter

import pytest
import yaml
from pandas import DataFrame

from tests.constants import ASSETS, TESTCASES
from tools.tabular import Tabular
from tools.vocabulary import JsonLD, JsonLDFrame


@pytest.mark.parametrize(
    "data,frame,expected_payload,expected_datapackage",
    argvalues=[
        itemgetter("data", "frame", "expected_payload", "expected_datapackage")(
            x
        )
        for x in TESTCASES
        if "expected_datapackage" in x
    ],
    ids=[x["name"] for x in TESTCASES if "expected_datapackage" in x],
)
def test_tabular_minimal(
    data: str,
    frame: JsonLDFrame,
    expected_payload: JsonLD,
    expected_datapackage: dict,
):
    """
    Test the Tabular class for creating a tabular representation of RDF datasets.

    Given:
    - RDF vocabulary data in JSON-LD format
    - A JSON-LD frame with @context definitions
    - An expected payload in JSON-LD format that is used instead
      of the computed projection

    When:
    - I create an instance of the Tabular class with the RDF data and frame
    - I call the set_dialect method to configure the CSV output settings

    Then:
    - The Tabular instance should be created successfully
    - The CSV dialect settings should be stored correctly in the instance
    """
    # Sample RDF data in JSON-LD format
    # Create an instance of the Tabular class
    tabular = Tabular(rdf_data=data, frame=frame)
    assert tabular
    df: DataFrame = tabular.load(data=expected_payload)
    assert df is not None
    raise NotImplementedError


@pytest.mark.parametrize(
    "vocabulary_ttl",
    argvalues=ASSETS.glob("**/*.ttl"),
    ids=[x.name for x in ASSETS.glob("**/*.ttl")],
)
def test_tabular_metadata(vocabulary_ttl, snapshot):
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
    tabular = Tabular(
        rdf_data=vocabulary_ttl, frame={"@context": {}}
    )  # Placeholder frame, replace with actual frame if needed
    vocab = tabular.datapackage()

    datapackage_yaml = snapshot / f"{vocab['name']}.datapackage.yaml"
    assert datapackage_yaml.exists()

    assert vocab == yaml.safe_load(datapackage_yaml.read_text()), (
        "Metadata extraction does not match expected snapshot"
    )
