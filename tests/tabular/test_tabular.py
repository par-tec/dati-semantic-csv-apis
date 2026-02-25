from operator import itemgetter
from pathlib import Path

import pytest
import yaml
from deepdiff import DeepDiff
from pandas import DataFrame

from tests.constants import TESTCASES
from tools.tabular import Tabular
from tools.tabular.validate import TabularValidator
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

    # Given the RDF data and frame...
    tabular = Tabular(rdf_data=data, frame=frame)
    assert tabular
    df: DataFrame = tabular.load(data={"@graph": expected_payload})
    assert df is not None
    tabular.set_dialect(**frictionless_dialect)

    # When I generate the complete datapackage stub...
    datapackage = tabular.datapackage_stub(resource_path=Path(output_csv.name))
    # ... then it has the expected value
    ddiff = DeepDiff(
        expected_datapackage, tabular.datapackage_stub(), ignore_order=True
    )
    assert ddiff["iterable_item_removed"]

    # When I set the datapackage ...
    tabular.datapackage = datapackage
    # ... then I can generate the CSV output
    tabular.to_csv(output_csv)
    assert output_csv.exists(), "CSV file was not created"
    datapackage_yaml.write_text(yaml.safe_dump(datapackage), encoding="utf-8")

    # When I read the datapackage and its data with Frictionless ...
    tabular_validator: TabularValidator = TabularValidator(
        datapackage_yaml, basepath=tmp_path.as_posix()
    )

    # ... then the data can be loaded.
    tabular_validator.load()
    # .. and the data is a subset of the original RDF graph.
    tabular_validator.validate(tabular.graph, min_triples=3)

    raise NotImplementedError
