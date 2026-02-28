from operator import itemgetter
from pathlib import Path
from typing import cast

import pytest
import yaml
from deepdiff import DeepDiff

from tests.constants import TESTCASES
from tools.tabular import Tabular
from tools.tabular.validate import TabularValidator
from tools.vocabulary import JsonLD, JsonLDFrame

TESTCASES_CSV_DIALECT = [
    {
        "name": "csv-default",
        "frictionless_dialect": {},
    },
    {
        "name": "csv-semicolon",
        "frictionless_dialect": {
            "delimiter": ";",
            "lineTerminator": "\n",
        },
    },
    {
        "name": "csv-semicolon-quote",
        "frictionless_dialect": {
            "delimiter": ";",
            "lineTerminator": "\n",
            "quoteChar": "'",
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
    snapshot: Path,
    request: pytest.FixtureRequest,
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
    destdir = snapshot / request.node.name
    destdir.mkdir(parents=True, exist_ok=True)
    datapackage_yaml = destdir / "datapackage.yaml"

    # Given the RDF data and frame...
    tabular = Tabular(rdf_data=data, frame=frame)
    uri = tabular.uri()
    output_csv = destdir / f"{Path(uri).stem}.csv"

    tabular.load(data=cast(JsonLD, {"@graph": expected_payload}))
    tabular.set_dialect(**frictionless_dialect)

    # When I generate the complete datapackage stub...
    datapackage = tabular.datapackage_stub(resource_path=Path(output_csv.name))
    # ... then it has the expected value
    ddiff = DeepDiff(expected_datapackage, datapackage, ignore_order=True)
    assert ddiff == {
        "dictionary_item_added": [
            "root['resources'][0]['scheme']",
            "root['resources'][0]['dialect']",
        ]
    }

    # When I set the datapackage metadata...
    tabular.datapackage = datapackage
    # ... then I can generate the CSV output
    tabular.to_csv(output_csv)
    assert output_csv.exists(), "CSV file was not created"
    datapackage_yaml.write_text(
        yaml.safe_dump(datapackage, sort_keys=True), encoding="utf-8"
    )

    # When I read the datapackage and its data with Frictionless ...
    tabular_validator: TabularValidator = TabularValidator(
        yaml.safe_load(datapackage_yaml.read_text()),
        basepath=destdir.as_posix(),
    )

    # ... then the data can be loaded.
    tabular_validator.load()
    # .. and the data is a subset of the original RDF graph.
    stats = tabular_validator.validate(tabular.graph, min_triples=3)
    assert stats["csv_triples"] >= 3, (
        "CSV-derived RDF graph has fewer triples than expected"
    )
    assert stats["csv_rows"] >= 3
