from operator import itemgetter
from pathlib import Path

import pytest

from tests.constants import TESTCASES
from tools.base import JsonLDFrame
from tools.tabular import Tabular


@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
@pytest.mark.parametrize(
    "context_key,should_be_filtered",
    [
        # Line 267: Skip JSON-LD keywords
        pytest.param(
            "@type",
            True,
            id="jsonld_keyword_type",
        ),
        pytest.param(
            "@context",
            True,
            id="jsonld_keyword_context",
        ),
        pytest.param("@id", True, id="jsonld_keyword_id"),
        # Line 270: Skip namespace declarations (ending with #, /, :)
        pytest.param(
            "skos",
            True,
            id="namespace_hash",
        ),
        pytest.param(
            "rdf",
            True,
            id="namespace_slash",
        ),
        pytest.param("ex", True, id="namespace_colon"),
        # Line 272: Skip ignored RDF properties
        pytest.param(
            "inScheme",
            True,
            id="ignored_inScheme",
        ),
        pytest.param(
            "broader",
            True,
            id="ignored_broader",
        ),
        # Valid fields that should NOT be filtered
        pytest.param(
            "level",
            False,
            id="valid_field",
        ),
    ],
)
def test_dataresource_stub_context_filters(
    data: str,
    frame: JsonLDFrame,
    context_key: str,
    should_be_filtered: bool,
):
    """
    Given: A Tabular instance initialized with RDF data and a JSON-LD frame containing
           various context keys including:
           - JSON-LD keywords (e.g., @type, @context, @id)
           - Namespace declarations ending with special characters (#, /, :)
           - Ignored RDF properties (e.g., inScheme, broader)
           - Valid field names (e.g., level)

    When: Generating a dataresource_stub by calling tabular.dataresource_stub()
          and extracting the field names from resource["schema"]["fields"]

    Then: The dataresource_stub should filter context keys according to these rules:
          - Keys starting with "@" should be filtered (line 267)
          - Keys whose string values end with "#", "/", or ":" should be filtered (line 270)
          - Keys in self.ignore_rdf_properties should be filtered (line 272)
          - Valid field names should NOT be filtered and appear in the field names list
    """

    tabular = Tabular(rdf_data=data, frame=frame)
    resource = tabular.dataresource_stub("test", Path("test.csv"))
    fields = resource["schema"]["fields"]
    field_names = [f["name"] for f in fields]

    is_filtered = context_key not in field_names

    assert is_filtered == should_be_filtered, (
        f"{context_key} - filtered out: {should_be_filtered}"
    )
