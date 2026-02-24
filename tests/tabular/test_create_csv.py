from pathlib import Path

import pytest
import yaml
from frictionless import Resource

from tests.constants import ASSETS, TESTDIR
from tools.projector import JsonLD, JsonLDFrame
from tools.tabular import create_csv

vocabularies = list(ASSETS.glob("**/*.data.yaml"))


testcases_yaml = TESTDIR / "testcases.yaml"
TESTCASES = yaml.safe_load(testcases_yaml.read_text())["testcases"]


@pytest.mark.parametrize(
    "vocabulary_data_yaml", vocabularies, ids=[x.name for x in vocabularies]
)
def test_create_csv(vocabulary_data_yaml):
    """
    Test the CSV creation from framed JSON-LD data.

    Given:
    - RDF vocabulary data
    - A JSON-LD frame with @context definitions

    When:
    - I frame the RDF data using the provided frame
    - I convert the framed data into a tabular format
    - I generate a CSV representation of the tabular data

    Then:
    - The generated CSV should match the expected CSV output
    """
    frame_yamlld = vocabulary_data_yaml.with_suffix("").with_suffix(
        ".frame.yamlld"
    )
    if not frame_yamlld.exists():
        raise pytest.skip(frame_yamlld.name)
    frame: JsonLDFrame = yaml.safe_load(frame_yamlld.read_text())

    with vocabulary_data_yaml.open(encoding="utf-8") as f:
        data: JsonLD = yaml.safe_load(f)

    # Generate CSV with proper quoting for strings
    expected_csv = vocabulary_data_yaml.with_suffix("").with_suffix(
        ".expected.csv"
    )

    df = create_csv(data, frame)
    df.to_csv(
        expected_csv.as_posix(),
        sep=",",
        index=False,
        quoting=1,  # csv.QUOTE_ALL - quote all fields
        escapechar="\\",
        doublequote=True,
        encoding="utf-8",
    )

    datapackage_yaml = vocabulary_data_yaml.parent / "datapackage.yaml"
    graph, context = data["@graph"], data["@context"]
    write_datapackage(graph, context, expected_csv)


# Return the value of the father
def get_father(x):
    return x[list(x)[-1]]


def write_datapackage(graph: JsonLD, context: JsonLD, dest_file):
    resource = Resource(data=graph)
    # print(resource)
    resource.infer()
    resource_dict = resource.to_dict()
    resource_dict.update(
        {"name": dest_file.stem, "path": dest_file.with_suffix(".csv").name}
    )
    resource_dict.pop("data")
    datapackage_yaml = Path(dest_file.parent / "datapackage.yaml")
    if datapackage_yaml.exists():
        datapackage = yaml.safe_load(datapackage_yaml.read_text())
        for r in datapackage["resources"]:
            if r["name"] == dest_file.stem:
                r.update(resource_dict)
                break
        else:
            datapackage["resources"].append(resource_dict)
    else:
        datapackage = {
            "name": dest_file.stem,
            "resources": [resource_dict],
        }
    datapackage["resources"][-1]["schema"]["x-jsonld-context"] = context
    if gtype := graph[0].get("@type"):
        datapackage["resources"][-1]["schema"]["x-jsonld-type"] = gtype
    datapackage_yaml.write_text(yaml.safe_dump(datapackage))
    # print("ho scritto: " +datapackage_yaml)
