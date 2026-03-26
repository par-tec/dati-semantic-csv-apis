import pytest

from tests.constants import ASSETS
from tests.harness import assert_snapshot_matches_data
from tools.tabular import Tabular
from tools.vocabulary import UnsupportedVocabularyError


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

    tabular = Tabular(rdf_data=vocabulary_ttl, frame={"@context": {}})
    try:
        tabular.uri()
    except UnsupportedVocabularyError:
        pytest.skip(
            "Vocabulary not supported for URI extraction, skipping test."
        )
    vocab = tabular.datapackage_stub()

    assert_snapshot_matches_data(
        snapshot_file=datapackage_yaml,
        current_data=vocab,
        update=True,
    )
