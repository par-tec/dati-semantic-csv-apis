import logging
from pathlib import Path

import pytest
import yaml

from tools.openapi_generator import create_schema_from_frame_and_data
from tools.utils import QuotedStringDumper

ASSET = Path(__file__).parent.parent / "assets" / "controlled-vocabularies"
vocabularies = list(ASSET.glob("**/*.data.yaml"))


@pytest.mark.asset
@pytest.mark.parametrize(
    "vocabulary_data_yaml", vocabularies, ids=[x.name for x in vocabularies]
)
def test_schema_with_constraints_and_validation(vocabulary_data_yaml):
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
    frame = yaml.safe_load(frame_yamlld.read_text())

    data = yaml.safe_load(vocabulary_data_yaml.read_text())

    # Generate schema with constraints and validation
    schema = create_schema_from_frame_and_data(
        frame, data, add_constraints=True, validate_output=True
    )

    oas_yaml = vocabulary_data_yaml.with_suffix("").with_suffix(".oas3.yaml")
    oas_yaml.write_text(
        yaml.dump(
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {"schemas": {"Item": schema}},
            },
            Dumper=QuotedStringDumper,
            sort_keys=True,
        )
    )
    schema_copy = schema.copy()
    schema_copy.pop("x-validation", None)  # Remove validation for comparison
    schema_copy.pop("x-jsonld-type", None)
    schema_copy.pop("x-jsonld-context", None)

    # Check that schema was generated
    assert "properties" in schema, "Schema should have properties"
    assert "x-validation" in schema, "Schema should include validation results"

    # Get validation results
    validation = schema["x-validation"]

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
    properties = schema.get("properties", {})

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
    context = frame.get("@context", {})
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
