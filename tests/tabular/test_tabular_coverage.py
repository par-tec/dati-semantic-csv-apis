"""
Test coverage for tools/tabular/__init__.py uncovered lines.

This module contains parametrized tests to cover specific edge cases
and error handling paths that are not covered by existing tests.

"""

from operator import itemgetter
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from tests.constants import TESTCASES
from tools.projector import JsonLDFrame
from tools.tabular import Tabular


# Test 1: Lines 153-155 - Lazy initialization of datapackage getter
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_datapackage_getter_lazy_init(data: str, frame: JsonLDFrame):
    """
    Given:
    - An instance of Tabular with RDF data and a JSON-LD frame

    When:
    - I access the datapackage property for the first time

    Then:
    - The datapackage should be created and returned
    - Further accesses should return the same instance without re-creating it
    """
    tabular = Tabular(rdf_data=data, frame=frame)

    # Access the property - should trigger lazy initialization
    datapackage = tabular.datapackage

    # Verify that a datapackage was created
    assert datapackage is not None

    # Accessing again should return the same instance
    datapackage2 = tabular.datapackage
    assert datapackage2 is datapackage


# Test 2: Lines 203-204 - FrictionlessException in datapackage_stub
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_datapackage_stub_invalid_metadata(data: str, frame: JsonLDFrame):
    """
    Test that datapackage_stub raises ValueError when create_datapackage
    generates invalid metadata that causes FrictionlessException.

    Covers lines 203-204:
    - except FrictionlessException as e:
    -     raise ValueError(f"Invalid datapackage: {_datapackage}") from e
    """
    tabular = Tabular(rdf_data=data, frame=frame)

    # Mock create_datapackage to return invalid metadata
    with patch("tools.tabular.create_datapackage") as mock_create:
        # Return a datapackage that will fail Package validation
        mock_create.return_value = {
            "name": "test",
            "resources": "invalid",  # Should be a list, not a string
        }

        with pytest.raises(ValueError, match="Invalid datapackage"):
            tabular.datapackage_stub()


# Test 3: Line 253 - Frame without @context
@pytest.mark.parametrize(
    "data,frame_dict",
    [
        pytest.param(
            TESTCASES[0]["data"],
            {"@type": "skos:Concept"},
            id="frame_without_context",
        ),
        pytest.param(
            TESTCASES[0]["data"],
            {},
            id="empty_frame",
        ),
    ],
)
def test_dataresource_stub_frame_without_context(data: str, frame_dict: dict):
    """
    Test that dataresource_stub raises ValueError when frame
    does not contain @context.

    Covers line 253:
    - raise ValueError("frame must contain @context")
    """
    # Create a frame without @context
    frame = JsonLDFrame({"@context": {}, "@type": "skos:Concept"})
    tabular = Tabular(rdf_data=data, frame=frame)

    # Manually set the frame to one without @context
    tabular.frame = frame_dict

    with pytest.raises(ValueError, match="frame must contain @context"):
        tabular.dataresource_stub("test", Path("test.csv"))


# Test 4: Lines 260-265 - Frame with @id field mapping
@pytest.mark.parametrize(
    "data,base_frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_dataresource_stub_with_id_field(data: str, base_frame: JsonLDFrame):
    """
    Test that dataresource_stub correctly handles frames with
    a field mapped to "@id" in the @context.

    Covers lines 260-265:
    - for key, value in context.items():
    -     if value == "@id":
    -         fields.append({"name": key, "type": "string"})
    -         break
    """
    # Create a frame with a field mapped to @id
    frame_with_id = {
        "@context": {
            "id": "@id",  # Map "id" to @id
            "label": "http://www.w3.org/2004/02/skos/core#prefLabel",
        },
        "@type": "http://www.w3.org/2004/02/skos/core#Concept",
    }

    frame = JsonLDFrame(frame_with_id)
    tabular = Tabular(rdf_data=data, frame=frame)

    resource = tabular.dataresource_stub("test", Path("test.csv"))

    # Verify that "id" field is present and is type "string"
    fields = resource["schema"]["fields"]
    id_field = next((f for f in fields if f["name"] == "id"), None)

    assert id_field is not None
    assert id_field["type"] == "string"
    # The id field should be the first one added
    assert fields[0] == id_field


# Test 5: Lines 267, 268-276, 270 - Context filters
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
@pytest.mark.parametrize(
    "context_key,expanded_value,should_be_filtered",
    [
        # Line 267: Skip JSON-LD keywords
        pytest.param(
            "@type",
            "http://www.w3.org/2004/02/skos/core#Concept",
            True,
            id="jsonld_keyword_type",
        ),
        pytest.param(
            "@context",
            "http://example.org/context",
            True,
            id="jsonld_keyword_context",
        ),
        pytest.param(
            "@id", "http://example.org/id", True, id="jsonld_keyword_id"
        ),
        # Line 270: Skip namespace declarations (ending with #, /, :)
        pytest.param(
            "skos",
            "http://www.w3.org/2004/02/skos/core#",
            True,
            id="namespace_hash",
        ),
        pytest.param(
            "rdf",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns/",
            True,
            id="namespace_slash",
        ),
        pytest.param("ex", "http://example.org:", True, id="namespace_colon"),
        # Line 272: Skip ignored RDF properties
        pytest.param(
            "inScheme",
            "http://www.w3.org/2004/02/skos/core#inScheme",
            True,
            id="ignored_inScheme",
        ),
        pytest.param(
            "broader",
            "http://www.w3.org/2004/02/skos/core#broader",
            True,
            id="ignored_broader",
        ),
        # Valid fields that should NOT be filtered
        pytest.param(
            "validField",
            "http://example.org/validField",
            False,
            id="valid_field",
        ),
    ],
)
def test_dataresource_stub_context_filters(
    data: str,
    frame: JsonLDFrame,
    context_key: str,
    expanded_value: str,
    should_be_filtered: bool,
):
    """
    Test that dataresource_stub correctly filters out:
    - JSON-LD keywords (starting with @)
    - Namespace declarations (ending with #, /, :)
    - Ignored RDF properties

    Covers lines 267, 268-276, 270:
    - if key.startswith("@"): continue
    - if isinstance(value, str):
    -     if value.endswith(("#", "/", ":")): continue
    -     if value in self.ignore_rdf_properties: continue
    """
    tabular = Tabular(rdf_data=data, frame=frame)

    # Mock expand_context_to_absolute_uris to return our test case
    with patch("tools.tabular.expand_context_to_absolute_uris") as mock_expand:
        mock_expand.return_value = {context_key: expanded_value}

        resource = tabular.dataresource_stub("test", Path("test.csv"))
        fields = resource["schema"]["fields"]
        field_names = [f["name"] for f in fields]

        if should_be_filtered:
            assert context_key not in field_names, (
                f"{context_key} should be filtered out"
            )
        else:
            assert context_key in field_names, (
                f"{context_key} should NOT be filtered out"
            )


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
    Test that dataresource_stub correctly maps XSD types to field types.

    Note: expand_context_to_absolute_uris normally returns strings, not dicts.
    To test lines 277-286, we mock it to return a dict with @type.

    Covers lines 277-286:
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


# Test 7: Line 331 - Unsupported quoteChar
@pytest.mark.parametrize(
    "invalid_quotechar",
    [
        pytest.param("|", id="pipe"),
        pytest.param("`", id="backtick"),
        pytest.param("~", id="tilde"),
        pytest.param("", id="empty_string"),
    ],
)
def test_pandas_csv_dialect_unsupported_quotechar(invalid_quotechar: str):
    """
    Test that _pandas_csv_dialect raises ValueError for unsupported quoteChar.

    Covers line 331:
    - raise ValueError(f"Unsupported quoteChar '{self._dialect['quoteChar']}' in CSV dialect")
    """
    data = TESTCASES[0]["data"]
    frame = JsonLDFrame(TESTCASES[0]["frame"])

    tabular = Tabular(rdf_data=data, frame=frame)

    # Manually set an invalid quoteChar in the dialect
    tabular._dialect["quoteChar"] = invalid_quotechar

    with pytest.raises(
        ValueError,
        match=f"Unsupported quoteChar.*{invalid_quotechar}.*in CSV dialect",
    ):
        tabular._pandas_csv_dialect()


# Test 8: Lines 355, 357 - Empty projection in load()
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_load_empty_projection(data: str, frame: JsonLDFrame):
    """
    Test that load() raises ValueError when project() returns empty data.

    Covers lines 355, 357:
    - if not self.data:
    -     self.data = self.project(self.frame)
    - if not self.data:
    -     raise ValueError("No data to load.")
    """
    tabular = Tabular(rdf_data=data, frame=frame)

    # Mock project to return None
    with patch.object(tabular, "project", return_value=None):
        with pytest.raises(ValueError, match="No data to load"):
            tabular.load()

    # Also test with empty dict
    with patch.object(tabular, "project", return_value={}):
        with pytest.raises(ValueError, match="No data to load"):
            tabular.load()


# Test 9: Line 360 - Missing @graph in load()
@pytest.mark.parametrize(
    "invalid_data",
    [
        pytest.param({"@context": {}}, id="no_graph_key"),
        pytest.param({"@graph": []}, id="empty_graph"),
        pytest.param({"@graph": None}, id="null_graph"),
    ],
)
def test_load_missing_graph(invalid_data: dict):
    """
    Test that load() raises ValueError when data doesn't contain @graph
    or when @graph is empty/null.

    Covers line 360:
    - if not items:
    -     raise ValueError("Framed data must contain a @graph.")
    """
    data = TESTCASES[0]["data"]
    frame = JsonLDFrame(TESTCASES[0]["frame"])

    tabular = Tabular(rdf_data=data, frame=frame)

    with pytest.raises(ValueError, match="Framed data must contain a @graph"):
        tabular.load(data=invalid_data)


# Test 10: Line 378 - to_csv without datapackage
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_to_csv_without_datapackage(
    data: str, frame: JsonLDFrame, tmp_path: Path
):
    """
    Test that to_csv() raises ValueError when datapackage is not set.

    Covers line 378:
    - if not self._datapackage:
    -     raise ValueError("Datapackage descriptor is required...")
    """
    tabular = Tabular(rdf_data=data, frame=frame)

    # Load data but don't set datapackage
    tabular.load(data={"@graph": [{"id": "test", "label": "Test"}]})

    output_path = tmp_path / "test.csv"

    with pytest.raises(ValueError, match="Datapackage descriptor is required"):
        tabular.to_csv(str(output_path))


# Test 11: Line 383 - to_csv without dataframe
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_to_csv_without_dataframe(
    data: str, frame: JsonLDFrame, tmp_path: Path
):
    """
    Test that to_csv() raises ValueError when DataFrame is not loaded.

    Covers line 383:
    - if self.df is None:
    -     raise ValueError("DataFrame is not loaded...")
    """
    tabular = Tabular(rdf_data=data, frame=frame)

    # Set datapackage but don't load data
    datapackage = tabular.datapackage_stub(resource_path=Path("test.csv"))
    tabular.datapackage = datapackage

    output_path = tmp_path / "test.csv"

    with pytest.raises(ValueError, match="DataFrame is not loaded"):
        tabular.to_csv(str(output_path))


# Test 12: Lines 398-400 - to_csv without id column
@pytest.mark.parametrize(
    "data,frame,expected_payload",
    argvalues=[
        itemgetter("data", "frame", "expected_payload")(x)
        for x in TESTCASES[:1]
        if "expected_payload" in x
    ],
    ids=[x["name"] for x in TESTCASES[:1] if "expected_payload" in x],
)
def test_to_csv_without_id_column(
    data: str, frame: JsonLDFrame, expected_payload: list, tmp_path: Path
):
    """
    Test that to_csv() works correctly when DataFrame doesn't have 'id' column.
    This tests the branch where sorting by 'id' is skipped (lines 398-400).

    Covers lines 398-400:
    - if "id" in self.df.columns:
    -     self.df.sort_values(by=["id"], ignore_index=True, inplace=True)
    """
    tabular = Tabular(rdf_data=data, frame=frame)

    # Load normal data
    tabular.load(data={"@graph": expected_payload})

    # Verify we have data
    assert tabular.df is not None
    assert len(tabular.df) > 0

    # Create a modified datapackage that doesn't include 'id' in selected columns
    output_path = tmp_path / "test.csv"
    datapackage = tabular.datapackage_stub(resource_path=Path(output_path.name))

    # Remove 'id' field from the datapackage schema if present
    fields = datapackage["resources"][0]["schema"]["fields"]
    filtered_fields = [f for f in fields if f["name"] != "id"]

    # Ensure we have at least some fields
    if not filtered_fields:
        # If all fields were 'id', keep at least one other field
        pytest.skip("Test data doesn't have non-id fields")

    datapackage["resources"][0]["schema"]["fields"] = filtered_fields
    tabular.datapackage = datapackage

    # Now when to_csv is called, it will select only the filtered fields
    # and the DataFrame won't have 'id' column after filtering
    tabular.to_csv(str(output_path))

    # Verify CSV was created
    assert output_path.exists()

    # Read and verify
    df = pd.read_csv(output_path, quoting=1)
    assert "id" not in df.columns
    assert len(df) > 0
