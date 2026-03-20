import pytest

from tools.openapi.jsonschema import OAS3SchemaBuilder


def test_builder_does_not_add_linked_data_keywords(
    caplog: pytest.LogCaptureFixture,
):
    """
    Given:
    - A JSON object with properties that include JSON-LD keywords and non-keywords

    When:
    - I add generate a JSON Schema

    Then:
    - JSON-LD keywords are skipped with a warning in the logs
    - JSON-LD properties glitching around (e.g., with colons) are skipped with a warning in the logs
    - Non-JSON-LD properties are included in the schema
    """
    with caplog.at_level("DEBUG"):
        builder = OAS3SchemaBuilder()
        builder.add_object(
            {
                "@context": "http://example.com/context",
                "@id": "http://example.com/id",
                "@type": "ExampleType",
                "name": "Example Name",
                "foo": None,
            }
        )
        builder.add_object(
            {
                "@context": {
                    "@vocab": "http://example.com/context",
                    "skos": "http://www.w3.org/2004/02/skos/core#",
                },
                "@id": "http://example.com/id",
                "@type": "ExampleType",
                "name": "Example Name",
                "foo": "bar",
                "skos:notation": "Example Notation",
            }
        )

        schema = builder.to_schema()

        assert (
            "Skipping property '@context' that does not match variable name pattern"
            in caplog.text
        )
        assert (
            "Skipping property 'skos:notation' that does not match variable name pattern"
            in caplog.text
        )

    assert schema == {
        "$schema": "http://json-schema.org/schema#",
        "properties": {
            "foo": {
                "anyOf": [
                    {"type": "string"},
                    {"nullable": True, "type": "string"},
                ]
            },
            "name": {"type": "string"},
        },
        "required": ["foo", "name"],
        "type": "object",
    }
