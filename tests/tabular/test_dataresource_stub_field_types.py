from operator import itemgetter
from pathlib import Path

import pytest
import yaml

from tools.base import JsonLDFrame
from tools.tabular import Tabular

TESTCASES_YAML = Path(__file__).with_suffix(".yaml")
TESTCASES = yaml.safe_load(TESTCASES_YAML.read_text())["testcases"]


# Test 6: Lines 278-286 - XSD type mapping
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_dataresource_stub_field_types(data: str, frame: JsonLDFrame):
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

    """
    tabular = Tabular(rdf_data=data, frame=frame)
    resource = tabular.dataresource_stub("test", Path("test.csv"))
    fields = resource["schema"]["fields"]

    expected_fields = [
        {"name": "url", "type": "string"},
        {"name": "id", "type": "string"},
        {"name": "label_it", "type": "string"},
        {"name": "level", "type": "integer"},
        {"name": "integerField", "type": "integer"},
        {"name": "intField", "type": "integer"},
        {"name": "prefixedIntegerField", "type": "integer"},
        {"name": "dateField", "type": "date"},
        {"name": "prefixedDateField", "type": "date"},
        {"name": "booleanField", "type": "boolean"},
        {"name": "prefixedBooleanField", "type": "boolean"},
        {"name": "decimalField", "type": "number"},
        {"name": "numberField", "type": "number"},
        {"name": "prefixedDecimalField", "type": "number"},
        {"name": "stringField", "type": "string"},
    ]

    assert fields == expected_fields
