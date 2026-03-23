"""
Tests to store yamlld graph data in a datastore
and retrieve it back using APIs.

SELECT * from ateco
WHERE json_extract(_text, '$.level') = '1'
LIMIT 5

CREATE INDEX IF NOT EXISTS idx_ateco_level
ON ateco (json_extract(_text, '$.level'))


"""

import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine, text

from tests.constants import ASSETS, DATADIR, TESTCASES
from tools.base import (
    APPLICATION_LD_JSON_FRAMED,
    JsonLD,
    JsonLDFrame,
)
from tools.openapi import Apiable


@pytest.mark.skip(reason="Implemented in test_openapi_asset.")
@pytest.mark.asset
def test_create_db(snapshot):
    ateco_data_yaml = (
        DATADIR / "snapshots" / "ateco-2025" / "ateco-2025.data.yamlld"
    )
    with open(ateco_data_yaml) as f:
        data = yaml.safe_load(f)

    frame: JsonLDFrame = JsonLDFrame.load(
        fpath=ASSETS / "ateco-2025" / "ateco-2025.frame.yamlld"
    )
    assert "@graph" in data
    assert "@context" in data
    apiable = Apiable(data, frame=frame, format=APPLICATION_LD_JSON_FRAMED)
    data: JsonLD = apiable.create_api_data()
    sqlite_url = Path(f"{snapshot}/ateco-2025/ateco-2025.db")
    apiable.to_db(data=data["@graph"], datafile=sqlite_url, force=True)

    sqlite_con = f"sqlite:///{sqlite_url.as_posix()}"
    with create_engine(sqlite_con).connect() as conn:
        rows = conn.execute(text("SELECT _text FROM ateco")).mappings().all()

    from jsonschema import Draft7Validator

    schema = DATADIR / "snapshots" / "ateco-2025" / "ateco-2025.oas3.yaml"
    validator = Draft7Validator(yaml.safe_load(schema.read_text()))

    errors = [
        f"{e.json_path}: {e.message}"
        for r in rows
        for e in validator.iter_errors(json.loads(r["_text"]))
    ]
    assert not errors, "Invalid db._text JSON:\n" + "\n".join(errors[:5])


URI = "url"


@pytest.mark.skip(reason="TODO: Move to Data API.")
@pytest.mark.asset
def test_create_payload(snapshot):
    """
    Given the ateco sqlite dataset, create a payload to be served by APIs.

    - uri: the resource URI
    - id: the resource skos:identifier, that should be used to query the resource.
        This identifier is used by the API but it does not necessarily map to the
        resource URI.

    Example:

    - id: '1'
      label_it: Agenti chimici inorganici
      level: 1
      uri: https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale/grande_gruppo/1
      href: https://schema.gov.it/vocabularies/v1/vocabularies/inail/agente_causale/1

    - id: '1.1'
      label_it: Agenti chimici inorganici gruppo a
      level: 2
      uri: https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale/gruppo/1.1
      href: https://schema.gov.it/vocabularies/v1/vocabularies/inail/agente_causale/1.1

    - id: "11110103"
      label_it: Idruri
      level: 3
      uri: https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale/agente/11110103
      href: https://schema.gov.it/vocabularies/v1/vocabularies/inail/agente_causale/11110103
    """

    sqlite_url = f"sqlite:///{snapshot}/ateco-2025/ateco-2025.db"
    sqlite_engine = create_engine(sqlite_url)

    db = sqlite_engine
    api_base_url = (
        "https://api.schema.gov.it/catalog/vocabularies/istat/ateco-2025"
    )

    with db.connect() as conn:
        rows = conn.execute(text("SELECT * FROM ateco")).mappings().all()

    payload = []
    for row in rows:
        item_data = json.loads(row["_text"])
        item_data.update(
            {
                "uri": item_data.pop(URI),
                "href": f"{api_base_url}/{row['id']}",
            }
        )
        parent = item_data.get("parent")
        if isinstance(parent, (list,)):
            for i, p in enumerate(parent):
                parent[i] = {
                    "uri": p.pop(URI),
                }
                if p.get("id") is not None:
                    parent[i]["id"] = p["id"]
                    parent[i]["href"] = f"{api_base_url}/{p['id']}"

        payload.append(item_data)

    ateco_2025_api_yaml = snapshot / "ateco-2025" / "ateco-2025.api.yaml"
    with ateco_2025_api_yaml.open(mode="w") as fh:
        yaml.safe_dump(payload, stream=fh)

    print(payload[:3])
    raise NotImplementedError


@pytest.fixture
def apiable_from_testcase():
    """Return an Apiable built from the first TESTCASE that has turtle + frame."""
    from operator import itemgetter

    tc = next(tc for tc in TESTCASES if "data" in tc and "frame" in tc)
    turtle, frame_dict = itemgetter("data", "frame")(tc)
    return Apiable(turtle, JsonLDFrame(frame_dict))


def test_apiable_persistence_roundtrip(apiable_from_testcase, tmp_path):
    """to_db / from_db round-trip: data readable both via from_db and directly
    through APIDatabase, with identical items and correct @context."""
    from harvest_db_schema import APIDatabase

    apiable = apiable_from_testcase
    db_path = tmp_path / "data.db"
    data: JsonLD = apiable.create_api_data()

    apiable.to_db(data=data, datafile=db_path, force=True)

    jsonld_result = apiable.from_db(db_path)
    metadata = apiable.metadata()
    assert metadata.agency_id is not None
    assert metadata.name is not None
    with APIDatabase(db_path.as_posix()) as db:
        dataset = db.get_vocabulary_dataset(
            metadata.agency_id,
            metadata.name,
        )

    assert len(jsonld_result["@graph"]) > 0
    assert jsonld_result["@graph"] == dataset
    assert jsonld_result["@context"] == apiable.frame.context
