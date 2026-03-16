from pathlib import Path

import pytest
import yaml

from tests.constants import ASSETS
from tests.harness import assert_schema
from tools.base import APPLICATION_LD_JSON_FRAMED, JsonLD, JsonLDFrame
from tools.openapi import Apiable
from tools.utils import SafeQuotedStringDumper

vocabularies: list[Path] = list(ASSETS.glob("**/*.data.yaml"))


# @pytest.mark.skip(reason="TODO: Add data.")
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

    datafile_db = vocabulary_data_yaml.with_suffix("").with_suffix(".db")

    frame = JsonLDFrame.load(frame_yamlld)

    with vocabulary_data_yaml.open() as f:
        data = yaml.safe_load(f)

    _data: JsonLD = {"@graph": data["@graph"], "@context": frame.context}
    apiable = Apiable(
        _data,
        frame,
        format=APPLICATION_LD_JSON_FRAMED,
    )

    json_schema = apiable.json_schema(
        schema_instances=_data, add_constraints=True, validate_output=True
    )

    apiable.to_db(
        data=_data,
        datafile=datafile_db,
        force=True,
    )

    oas_yaml = vocabulary_data_yaml.with_suffix("").with_suffix(".oas3.yaml")
    oas_yaml.write_text(
        yaml.dump(
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {"schemas": {"Item": json_schema}},
            },
            Dumper=SafeQuotedStringDumper,
            sort_keys=True,
        )
    )
    schema_copy = json_schema.copy()
    assert_schema(schema_copy, frame)
