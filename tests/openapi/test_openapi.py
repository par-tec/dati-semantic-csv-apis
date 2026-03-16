import json
from operator import itemgetter
from pathlib import Path

import pytest
import yaml
from deepdiff import DeepDiff
from jsonschema import Draft7Validator
from sqlalchemy import create_engine, text

# from rdflib.plugins.serializers.jsonld import from_rdf
# from rdflib.plugins.parsers.jsonld import to_rdf
from tests.constants import ASSETS, SNAPSHOTS, TESTCASES
from tests.harness import assert_schema, compare_data
from tools.base import APPLICATION_LD_JSON_FRAMED, JsonLD, JsonLDFrame, RDFText
from tools.openapi import (
    Apiable,
    OpenAPI,
)
from tools.utils import SafeQuotedStringDumper
from tools.vocabulary import UnsupportedVocabularyError

vocabularies: list[Path] = list(ASSETS.glob("**/*.data.yaml"))


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

    frame = JsonLDFrame(frame)
    apiable = Apiable(
        {"@graph": data, "@context": frame.context},
        frame,
        format=APPLICATION_LD_JSON_FRAMED,
    )

    schema_instances: JsonLD = apiable.create_api_data()
    assert schema_instances, "Expected non-empty schema instances"
    json_schema = apiable.json_schema(
        schema_instances=schema_instances,
        add_constraints=True,
        validate_output=True,
    )
    jsonschema_oas3_yaml.write_text(
        yaml.dump(json_schema, Dumper=SafeQuotedStringDumper, sort_keys=True)
    )
    delta = DeepDiff(json_schema, expected_jsonschema, ignore_order=True)

    for expected_equals in (
        "properties",
        "x-jsonld-context",
    ):
        assert expected_equals not in delta

    assert_schema(schema_copy=json_schema, frame=frame)


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

    frame = JsonLDFrame(frame)
    apiable = Apiable(turtle, frame)

    try:
        openapi: OpenAPI = apiable.openapi()
    except UnsupportedVocabularyError as e:
        pytest.skip(f"Unsupported vocabulary: {e}")
    compare_data(oas3_yaml, current_data=openapi, update=True)


@pytest.mark.parametrize(
    "turtle,frame,expected_jsonschema",
    argvalues=[
        itemgetter("data", "frame", "expected_jsonschema")(x)
        for x in TESTCASES
        if "expected_jsonschema" in x
    ],
    ids=[x["name"] for x in TESTCASES if "expected_jsonschema" in x],
)
def test_openapi_datastore(
    turtle: RDFText,
    frame: JsonLDFrame,
    expected_jsonschema: dict,
    snapshot_dir: Path,
    request: pytest.FixtureRequest,
):
    """
    Test the OpenAPI schema generation from JSON-LD frames and data.

    Given:
    - RDF vocabulary data in JSON-LD format
    - A JSON-LD frame with @context definitions

    When:
    - I create an instance of the Apiable class with the RDF data and frame
    - Generate the API payload
    - I create a datastore with the above payload

    Then:
    - The datastore should be created successfully
    - I can query the datastore
    - The datastore content respects the JSON Schema
    """
    oas3_yaml = SNAPSHOTS / "base" / f"{request.node.callspec.id}.oas3.yaml"
    validator = Draft7Validator(expected_jsonschema)
    # Given an RDF vocabulary and a frame...
    frame = JsonLDFrame(frame)

    # When I create an Apiable instance...
    apiable = Apiable(turtle, frame)

    try:
        # .. and generate the iterable API payload...
        data: JsonLD = apiable.create_api_data()
        assert data
        # ... and serialize it to a SQLite database
        apiable.to_db(
            data=data,
            datafile=snapshot_dir / "data.db",
            force=True,
        )
    except UnsupportedVocabularyError as e:
        pytest.skip(f"Unsupported vocabulary: {e}")

    # Then I can query the datastore ...
    with create_engine(
        f"sqlite:///{snapshot_dir / 'data.db'}"
    ).connect() as conn:
        rows = (
            conn.execute(text(f"SELECT _text FROM {apiable.uri_uuid()}"))
            .mappings()
            .all()
        )
    # ... and the content should be valid according to the JSON Schema
    errors = [
        f"{e.json_path}: {e.message}"
        for r in rows
        for e in validator.iter_errors(json.loads(r["_text"]))
    ]
    assert not errors, "Invalid db._text JSON:\n" + "\n".join(errors[:5])
    compare_data(
        snapshot_file=oas3_yaml,
        current_data=expected_jsonschema,
        update=True,
    )
