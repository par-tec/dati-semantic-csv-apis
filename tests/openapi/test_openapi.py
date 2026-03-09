import logging
from operator import itemgetter
from pathlib import Path

import pytest
import yaml
from deepdiff import DeepDiff

# from rdflib.plugins.serializers.jsonld import from_rdf
# from rdflib.plugins.parsers.jsonld import to_rdf
from tests.constants import ASSETS, TESTCASES
from tests.harness import compare_data
from tools.base import JsonLDFrame, RDFText
from tools.openapi.openapi_generator import (
    Apiable,
    OpenAPI,
)
from tools.utils import QuotedStringDumper

vocabularies = list(ASSETS.glob("**/*.data.yaml"))


@pytest.mark.parametrize(
    "data,frame,expected_jsonschema",
    argvalues=[
        itemgetter("expected_payload", "frame", "expected_jsonschema")(x)
        for x in TESTCASES
        if "expected_jsonschema" in x
    ],
    ids=[x["name"] for x in TESTCASES if "expected_jsonschema" in x],
)
def test_openapi_minimal(
    data: dict,
    frame: JsonLDFrame,
    expected_jsonschema: dict,
    snapshot_dir: Path,
):
    """
    Test the OpenAPI schema generation from JSON-LD frames and data.

    Given:
    - RDF vocabulary data in JSON-LD format
    - A JSON-LD frame with @context definitions

    When:
    - I create an instance of the Apiable class with the RDF data and frame
    - I generate the complete json_schema stub

    Then:
    - The OpenAPI schema should be created successfully
    - The schema should include the expected properties and constraints
    - The schema should be valid according to the OpenAPI specification
    """
    jsonschema_oas3_yaml = snapshot_dir / "oas3_schema.yaml"

    # apiable = Apiable(data, frame)
    # json_schema = apiable.json_schema()
    frame = JsonLDFrame(frame)
    apiable = Apiable(
        {"@graph": data, "@context": frame.context},
        frame,
    )

    json_schema = apiable.json_schema(
        add_constraints=True, validate_output=True
    )
    jsonschema_oas3_yaml.write_text(
        yaml.dump(json_schema, Dumper=QuotedStringDumper, sort_keys=True)
    )
    delta = DeepDiff(json_schema, expected_jsonschema, ignore_order=True)

    for expected_equals in (
        "properties",
        "x-jsonld-context",
    ):
        assert expected_equals not in delta

    assert_schema(json_schema, frame)


@pytest.mark.parametrize(
    "turtle,frame,expected_jsonschema",
    argvalues=[
        itemgetter("data", "frame", "expected_jsonschema")(x)
        for x in TESTCASES
        if "expected_jsonschema" in x
    ],
    ids=[x["name"] for x in TESTCASES if "expected_jsonschema" in x],
)
def test_openapi_metadata(
    turtle: RDFText,
    frame: JsonLDFrame,
    expected_jsonschema: dict,
    snapshot_dir: Path,
):
    """
    Test the OpenAPI schema generation from JSON-LD frames and data.

    Given:
    - RDF vocabulary data in JSON-LD format
    - A JSON-LD frame with @context definitions

    When:
    - I create an instance of the Apiable class with the RDF data and frame
    - I generate the complete OpenAPI stub

    Then:
    - The OpenAPI schema should be created successfully
    - The schema should include the expected properties and constraints
    - The schema should be valid according to the OpenAPI specification
    """
    oas3_yaml = snapshot_dir / "oas3.yaml"

    # apiable = Apiable(data, frame)
    # json_schema = apiable.json_schema()
    frame = JsonLDFrame(frame)
    apiable = Apiable(turtle, frame)

    openapi: OpenAPI = apiable.openapi()
    oas3_yaml.write_text(
        yaml.dump(openapi, Dumper=QuotedStringDumper, sort_keys=True)
    )

    compare_data(oas3_yaml, oas3_yaml)
    raise NotImplementedError


@pytest.mark.skip(reason="TODO: Add data.")
@pytest.mark.asset
@pytest.mark.parametrize(
    "vocabulary_data_yaml", vocabularies, ids=[x.name for x in vocabularies]
)
def test_schema_with_constraints_and_validation(vocabulary_data_yaml: Path):
    """
    Test that JSON Schema is enhanced with constraints from context
    and validates the actual vocabulary data.

    Given:
    - RDF vocabulary data
    - A JSON-LD frame with @context definitions

    When:
    - I generate a schema with constraints from the frame
    - I validate the framed data against the schema

    Then:
    - The schema should include appropriate constraints (minimum, pattern, etc.)
    - The validation should pass or report specific errors
    - The schema should include validation results in x-validation
    """
    frame_yamlld = vocabulary_data_yaml.with_suffix("").with_suffix(
        ".frame.yamlld"
    )
    if not frame_yamlld.exists():
        raise pytest.skip(frame_yamlld.name)

    frame = JsonLDFrame.load(frame_yamlld)

    with vocabulary_data_yaml.open() as f:
        data = yaml.safe_load(f)

    apiable = Apiable({"@graph": data, "@context": frame.context}, frame)

    json_schema = apiable.json_schema(
        add_constraints=True, validate_output=True
    )

    oas_yaml = vocabulary_data_yaml.with_suffix("").with_suffix(".oas3.yaml")
    oas_yaml.write_text(
        yaml.dump(
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {"schemas": {"Item": json_schema}},
            },
            Dumper=QuotedStringDumper,
            sort_keys=True,
        )
    )
    schema_copy = json_schema.copy()
    assert_schema(schema_copy, frame)


def assert_schema(schema_copy: OpenAPI, frame: JsonLDFrame) -> None:
    """ """
    validation = schema_copy.pop("x-validation", None)
    x_jsonld_type = schema_copy.pop("x-jsonld-type", None)
    assert x_jsonld_type
    x_jsonld_context = schema_copy.pop("x-jsonld-context", None)
    assert x_jsonld_context
    # Check that schema was generated
    assert validation is not None, "Schema should include x-validation results"

    # Log validation results for inspection
    logging.info("Validation results for %s:", frame.get("@type"))
    logging.info("  Valid: %s", validation["valid"])
    logging.info("  Errors: %d", validation["error_count"])

    if validation["errors"]:
        for error in validation["errors"][:5]:  # Log first 5 errors
            logging.warning(
                "  - %s at path %s", error["message"], error["path"]
            )

    # Check that constraints were added where expected
    properties = schema_copy.get("properties", {})
    assert properties, "Schema should have properties"

    # Check for integer constraints (e.g., level field with xsd:integer)
    for field_name, prop_schema in properties.items():
        if prop_schema.get("type") in ["integer", "number"]:
            # Should have minimum constraint from xsd:integer
            if field_name == "level":
                assert "minimum" in prop_schema, (
                    f"Integer field '{field_name}' should have minimum constraint"
                )
                assert "maximum" in prop_schema, (
                    "Level field should have maximum constraint"
                )
                logging.info(
                    "Field '%s' has constraints: minimum=%s, maximum=%s",
                    field_name,
                    prop_schema.get("minimum"),
                    prop_schema.get("maximum"),
                )

    # Check for string constraints (e.g., SKOS notation)
    context = frame.context
    for field_name, field_def in context.items():
        if isinstance(field_def, dict) and "@id" in field_def:
            predicate = field_def["@id"]
            if "notation" in predicate and field_name in properties:
                prop_schema = properties[field_name]
                if prop_schema.get("type") == "string":
                    assert "pattern" in prop_schema, (
                        f"Notation field '{field_name}' should have pattern constraint"
                    )
                    assert "minLength" in prop_schema, (
                        f"Notation field '{field_name}' should have minLength constraint"
                    )
                    logging.info(
                        "Field '%s' (notation) has pattern: %s",
                        field_name,
                        prop_schema.get("pattern"),
                    )

    # The validation should ideally pass, but if there are errors,
    # they should be specific and actionable
    if not validation["valid"]:
        logging.warning(
            "Validation failed with %d errors", validation["error_count"]
        )
        assert validation["error_count"] > 0, "If not valid, should have errors"
        # Errors should have proper structure
        for error in validation["errors"]:
            assert "message" in error, "Error should have message"
            assert "path" in error, "Error should have path"
    else:
        logging.info(
            "✓ All framed vocabulary data validates against the enhanced schema"
        )
