from pathlib import Path

import yaml
from frictionless import Resource

from tests.constants import ASSETS
from tools.projector import JsonLD

vocabularies = list(ASSETS.glob("**/*.data.yaml"))


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
