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

import pandas as pd
import pytest
import yaml

from tests.constants import DATADIR, TESTDIR

sqlite_engine = "sqlite:///test_ateco.db"


def _filter(item):
    # Remove @type.
    item.pop("@type", None)
    _text: str = json.dumps(item)
    item["_text"] = _text
    return {
        k: v
        for k, v in item.items()
        if isinstance(v, (int, float, bool, str, type(None)))
    }


@pytest.mark.skip
def test_store_ateco():
    ateco_data_yaml = (
        DATADIR / "snapshots" / "ateco-2025" / "ateco-2025.data.yamlld"
    )
    with open(ateco_data_yaml) as f:
        data = yaml.safe_load(f)
    data = data["@graph"][:10]
    json.dump(data, open(TESTDIR / "ateco-2025.data.json", "w"), indent=2)


def test_load_ateco():
    data = json.load(open(TESTDIR / "ateco-2025.data.json"))
    ateco_data_yaml = (
        DATADIR / "snapshots" / "ateco-2025" / "ateco-2025.data.yamlld"
    )
    with open(ateco_data_yaml) as f:
        data = yaml.safe_load(f)

    data = (_filter(item) for item in data["@graph"])
    df = pd.DataFrame(data)

    df.to_sql("ateco", sqlite_engine, if_exists="replace", index=False)

    raise NotImplementedError


def test_create_payload():
    """
    Given the ateco dataset, create a payload to be served by APIs.

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


def test_create_uuid():
    pass
