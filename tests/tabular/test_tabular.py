from operator import itemgetter
from pathlib import Path

import pytest
import yaml
from deepdiff import DeepDiff
from pandas import DataFrame

from tests.constants import ASSETS, TESTCASES
from tools.tabular import Tabular
from tools.vocabulary import JsonLD, JsonLDFrame

TESTCASES_CSV_DIALECT = [
    {
        "name": "Default CSV dialect",
        "frictionless_dialect": {},
    },
    {
        "name": "Custom CSV dialect with semicolon delimiter",
        "frictionless_dialect": {
            "delimiter": ";",
            "lineTerminator": "\n",
        },
    },
]


@pytest.mark.parametrize(
    "data,frame,expected_payload,expected_datapackage",
    argvalues=[
        itemgetter("data", "frame", "expected_payload", "expected_datapackage")(
            x
        )
        for x in TESTCASES
        if "expected_datapackage" in x
    ],
    ids=[x["name"] for x in TESTCASES if "expected_datapackage" in x],
)
@pytest.mark.parametrize(
    "frictionless_dialect",
    argvalues=[
        itemgetter("frictionless_dialect")(x)
        for x in TESTCASES_CSV_DIALECT
        if "frictionless_dialect" in x
    ],
    ids=[
        x["name"] for x in TESTCASES_CSV_DIALECT if "frictionless_dialect" in x
    ],
)
def test_tabular_minimal(
    data: str,
    frame: JsonLDFrame,
    expected_payload: JsonLD,
    expected_datapackage: dict,
    frictionless_dialect: dict,
    tmp_path: Path,
):
    """
    Test the Tabular class for creating a tabular representation of RDF datasets.

    Given:
    - RDF vocabulary data in JSON-LD format
    - A JSON-LD frame with @context definitions
    - An expected payload in JSON-LD format that is used instead
      of the computed projection

    When:
    - I create an instance of the Tabular class with the RDF data and frame
    - I call the set_dialect method to configure the CSV output settings
    - I generate the complete datapackage stub

    Then:
    - The Tabular instance should be created successfully
    - The CSV is serialized with the correct dialect settings
    - The metadata method should return a valid datapackage descriptor dictionary
    - The generated CSV should match the expected payload when projected and serialized
    - The CSV should be parsable by the Frictionless framework without errors
    """
    output_csv = tmp_path / "output.csv"
    datapackage_yaml = tmp_path / "datapackage.yaml"
    tabular = Tabular(rdf_data=data, frame=frame)
    assert tabular
    df: DataFrame = tabular.load(data={"@graph": expected_payload})
    assert df is not None
    tabular.set_dialect(**frictionless_dialect)

    datapackage = tabular.datapackage(resource_path=Path(output_csv.name))
    ddiff = DeepDiff(
        expected_datapackage, tabular.datapackage(), ignore_order=True
    )

    tabular.to_csv(output_csv)

    datapackage_yaml.write_text(yaml.safe_dump(datapackage), encoding="utf-8")
    from frictionless import Package

    package = Package(datapackage_yaml.as_posix())
    resource = package.resources[0]
    validation_result = resource.validate()
    errors = validation_result[0].errors
    assert not errors, f"Frictionless validation errors: {errors}"
    resource.rows
    assert output_csv.exists(), "CSV file was not created"

    assert ddiff["iterable_item_removed"]
    raise NotImplementedError


@pytest.mark.parametrize(
    "vocabulary_ttl",
    argvalues=ASSETS.glob("**/*.ttl"),
    ids=[x.name for x in ASSETS.glob("**/*.ttl")],
)
def test_tabular_metadata(vocabulary_ttl, snapshot):
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
    tabular = Tabular(
        rdf_data=vocabulary_ttl, frame={"@context": {}}
    )  # Placeholder frame, replace with actual frame if needed
    vocab = tabular.datapackage()

    datapackage_yaml = snapshot / f"{vocab['name']}.datapackage.yaml"
    assert datapackage_yaml.exists()

    assert vocab == yaml.safe_load(datapackage_yaml.read_text()), (
        "Metadata extraction does not match expected snapshot"
    )
