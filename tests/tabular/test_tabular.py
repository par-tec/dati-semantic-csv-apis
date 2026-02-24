from operator import itemgetter

import pytest
from pandas import DataFrame

from tests.constants import ASSETS, TESTCASES
from tools.tabular import Tabular


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
def test_tabular(data, frame, expected_payload, expected_datapackage):
    """
    Test the Tabular class for creating a tabular representation of RDF datasets.

    Given:
    - RDF vocabulary data in JSON-LD format
    - A JSON-LD frame with @context definitions

    When:
    - I create an instance of the Tabular class with the RDF data and frame
    - I call the set_dialect method to configure the CSV output settings

    Then:
    - The Tabular instance should be created successfully
    - The CSV dialect settings should be stored correctly in the instance
    """
    # Sample RDF data in JSON-LD format
    # Create an instance of the Tabular class
    tabular = Tabular(data=data, frame=frame)
    assert tabular
    df: DataFrame = tabular.load()
    assert df is not None
    raise NotImplementedError


@pytest.mark.parametrize(
    "vocabulary_ttl",
    argvalues=ASSETS.glob("**/*.ttl"),
    ids=[x.name for x in ASSETS.glob("**/*.ttl")],
)
def test_tabular_metadata(vocabulary_ttl):
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
        data=None, frame={"@context": {}}
    )  # Placeholder frame, replace with actual frame if needed
    vocab = tabular.metadata(rdf_data=vocabulary_ttl, vocabulary_uri="")
    raise NotImplementedError("Missing frame")
