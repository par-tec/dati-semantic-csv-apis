from operator import itemgetter
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.constants import TESTCASES
from tools.base import JsonLDFrame
from tools.tabular import Tabular


# Test 6: Lines 278-286 - XSD type mapping
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
@pytest.mark.parametrize(
    "xsd_type,expected_field_type",
    [
        # Line 279-280: integer/int types
        pytest.param(
            "http://www.w3.org/2001/XMLSchema#integer",
            "integer",
            id="xsd_integer",
        ),
        pytest.param(
            "http://www.w3.org/2001/XMLSchema#int", "integer", id="xsd_int"
        ),
        pytest.param("xsd:integer", "integer", id="prefixed_integer"),
        # Line 281-282: date type
        pytest.param(
            "http://www.w3.org/2001/XMLSchema#date", "date", id="xsd_date"
        ),
        pytest.param("xsd:date", "date", id="prefixed_date"),
        # Line 283-284: boolean type
        pytest.param(
            "http://www.w3.org/2001/XMLSchema#boolean",
            "boolean",
            id="xsd_boolean",
        ),
        pytest.param("xsd:boolean", "boolean", id="prefixed_boolean"),
        # Line 285-286: number/decimal types
        pytest.param(
            "http://www.w3.org/2001/XMLSchema#decimal",
            "number",
            id="xsd_decimal",
        ),
        pytest.param(
            "http://www.w3.org/2001/XMLSchema#number", "number", id="xsd_number"
        ),
        pytest.param("xsd:decimal", "number", id="prefixed_decimal"),
        # Default: string type (lines 268, 276)
        pytest.param(
            "http://www.w3.org/2001/XMLSchema#string", "string", id="xsd_string"
        ),
    ],
)
def test_dataresource_stub_field_types(
    data: str, frame: JsonLDFrame, xsd_type: str, expected_field_type: str
):
    """
    Given: A Tabular instance initialized with RDF data and a JSON-LD frame
           AND expand_context_to_absolute_uris is mocked to return a dictionary
           containing a field "testField" with an @type property set to a specific XSD type
           (e.g., xsd:integer, xsd:date, xsd:boolean, xsd:decimal, xsd:string)

           Note: This mock is necessary because expand_context_to_absolute_uris normally
           returns strings (URIs), not dictionaries, making lines 277-286 unreachable
           in normal operation. The mock simulates a scenario where the expanded context
           contains type information in dictionary format.

    When: Calling tabular.dataresource_stub() to generate a Frictionless data resource
          which extracts field definitions from the frame's @context and determines
          field types based on XSD type annotations

    Then: The generated data resource should contain a field named "testField" with
          the correct type mapping according to these rules (lines 278-286):
          - XSD types containing "integer" or "int" → "integer" field type (lines 279-280)
          - XSD types containing "date" → "date" field type (lines 281-282)
          - XSD types containing "boolean" → "boolean" field type (lines 283-284)
          - XSD types containing "number" or "decimal" → "number" field type (lines 285-286)
          - All other XSD types → "string" field type (default, line 276)

    Covers lines 277-286 of tools/tabular/__init__.py:
    - if isinstance(value, dict):
    -     xsd_type = value.get("@type", "")
    -     if "integer" in xsd_type or "int" in xsd_type:
    -         field_type = "integer"
    -     elif "date" in xsd_type:
    -         field_type = "date"
    -     elif "boolean" in xsd_type:
    -         field_type = "boolean"
    -     elif "number" in xsd_type or "decimal" in xsd_type:
    -         field_type = "number"
    """
    tabular = Tabular(rdf_data=data, frame=frame)
    # resource = tabular.dataresource_stub("test", Path("test.csv"))
    # fields = resource["schema"]["fields"]
    #
    # test_field = next((f for f in fields if f["name"] == "testField"), None)
    # assert test_field is not None
    # assert test_field["type"] == expected_field_type
    # return

    # Mock expand_context_to_absolute_uris to return a dict with @type
    # This is needed because normally it returns strings, making lines 277-286 unreachable
    with patch("tools.tabular.expand_context_to_absolute_uris") as mock_expand:
        mock_expand.return_value = {
            "testField": {
                "@id": "http://example.org/testField",
                "@type": xsd_type,
            }
        }

        resource = tabular.dataresource_stub("test", Path("test.csv"))
        fields = resource["schema"]["fields"]

        test_field = next((f for f in fields if f["name"] == "testField"), None)
        assert test_field is not None
        assert test_field["type"] == expected_field_type
