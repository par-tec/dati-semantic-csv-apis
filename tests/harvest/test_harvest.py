"""
This file harvests vocabulary repository URLs from schema.gov.it/sparql.
"""

import json
import logging
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from harvest_db_schema import APIDatabase, build_vocabulary_uuid
from tests.constants import SNAPSHOTS
from tools.base import JsonLD

SPARQL_ENDPOINT = "https://schema.gov.it/sparql"
SPARQL_QUERY = """
PREFIX NDC: <https://w3id.org/italia/onto/NDC/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT * WHERE {

    ?vocabulary_uri
        dcat:distribution ?distribution ;
        dcterms:rightsHolder ?rights_holder ;
        NDC:keyConcept ?key_concept .

    ?distribution
        dcat:downloadURL ?download_url ;
        dcterms:format
        <http://publications.europa.eu/resource/authority/file-type/RDF_TURTLE> .
}
"""
SQLITE_URL = "sqlite:///harvest.db"


@dataclass(frozen=True)
class VocabularyRepository:
    download_url: str
    distribution: str
    key_concept: str
    rights_holder: str
    vocabulary_uri: str

    @property
    def vocabulary_uuid(self) -> str:
        return build_vocabulary_uuid(
            agency_id=self.agency_id,
            key_concept=self.key_concept,
        )

    @property
    def agency_id(self) -> str:
        return Path(self.rights_holder).name.lower()


def harvest_vocabularies(sparql_endpoint: str) -> list[dict[str, str]]:
    """
    Query the remote SPARQL endpoint and return discovered vocabularies.
    """
    log = logging.getLogger(__name__)
    log.info("Starting vocabulary harvesting process from %s", sparql_endpoint)

    params = {
        "query": SPARQL_QUERY,
        "format": "application/sparql-results+json",
    }
    headers = {"Accept": "application/sparql-results+json"}
    url = f"{sparql_endpoint}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request) as response:
        payload = json.loads(response.read().decode("utf-8"))

    bindings = payload.get("results", {}).get("bindings", [])
    return [
        {
            variable: binding[variable]["value"]
            for variable in binding
            if "value" in binding[variable]
        }
        for binding in bindings
    ]


def test_harvest_vocabularies():
    vocabularies = harvest_vocabularies(SPARQL_ENDPOINT)
    assert len(vocabularies) > 0, "No vocabularies found at the SPARQL endpoint"
    for vocab in vocabularies:
        assert "vocabulary_uri" in vocab, "Vocabulary URI missing in result"
        assert "download_url" in vocab, "Download URL missing in result"
        assert "rights_holder" in vocab, "Rights holder missing in result"
        assert "key_concept" in vocab, "Key concept missing in result"


def collect_data(repository: VocabularyRepository, destination_folder: Path):
    """
    Collect datasets from a repository URL, including:
    - *.data.yamlld files with the data to be published by the API
    - *.frame.yamlld files with the framing context to be used for the API
    - *.oas3.yaml files with the OpenAPI specification to be used for the API
    """
    destination_folder.mkdir(parents=True, exist_ok=True)

    source_url: str = repository.download_url
    source_stem: str = source_url.removesuffix(".ttl")
    key_concept: str = repository.key_concept

    remote_to_local = {
        source_url: destination_folder / f"{key_concept}.ttl",
        f"{source_stem}.frame.yamlld": destination_folder
        / f"{key_concept}.frame.yamlld",
        f"{source_stem[: -len(key_concept)]}openapi.yaml": destination_folder
        / f"{key_concept}.oas3.yaml",
        f"{source_stem}.data.yamlld": destination_folder
        / f"{key_concept}.data.yamlld",
    }

    for remote_url, local_path in remote_to_local.items():
        try:
            with urllib.request.urlopen(remote_url) as response:
                local_path.write_bytes(response.read())
        except Exception as e:
            logging.getLogger(__name__).error(
                "Failed to download %s: %s", remote_url, e
            )
    return {
        "path": destination_folder.as_posix(),
        "vocabulary_ttl": destination_folder / f"{repository.key_concept}.ttl",
        **repository.__dict__,
    }


ATECO = VocabularyRepository(
    # "download_url"="https://github.com/istat/ndc-ontologie-vocabolari-controllati/tree/main/assets/controlled-vocabularies/economy/ateco-2025/ateco-2025.ttl",
    download_url="https://raw.githubusercontent.com/par-tec/dati-semantic-csv-apis/refs/heads/assets/assets/controlled-vocabularies/ateco-2025/ateco-2025.ttl",
    distribution="https://w3id.org/italia/data/distribution/Ateco2025-RDF-Turtle",
    key_concept="ateco-2025",
    rights_holder="https://w3id.org/italia/data/public-organization/ISTAT",
    vocabulary_uri="https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
)
AGENTE_CAUSALE = VocabularyRepository(
    distribution="https://w3id.org/italia/work-accident/data/adm_serv/distribution/AC_RDF_TURTLE",
    download_url="https://raw.githubusercontent.com/par-tec/dati-semantic-csv-apis/refs/heads/assets/assets/controlled-vocabularies/agente_causale/latest/agente_causale.ttl",
    key_concept="agente_causale",
    rights_holder="https://w3id.org/italia/work-accident/data/organization/inail",
    vocabulary_uri="https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale",
)

SNAPSHOT_REPOSITORIES = {
    ATECO.key_concept: ATECO,
    AGENTE_CAUSALE.key_concept: AGENTE_CAUSALE,
}


def test_collect_data(tmp_path: Path):
    data = ATECO
    collected_data = collect_data(data, tmp_path)
    vocabulary_ttl = Path(collected_data["vocabulary_ttl"])
    assert vocabulary_ttl.with_suffix(".oas3.yaml").exists()
    assert vocabulary_ttl.with_suffix(".frame.yamlld").exists()
    assert vocabulary_ttl.with_suffix(".data.yamlld").exists()


def _sqlite_path(db_url: str) -> str:
    prefix = "sqlite:///"
    if not db_url.startswith(prefix):
        raise ValueError(f"Unsupported database URL: {db_url}")
    return db_url.removeprefix(prefix)


def _remove_jsonld_keys(value):
    if isinstance(value, dict):
        return {
            key: _remove_jsonld_keys(item)
            for key, item in value.items()
            if not key.startswith("@")
        }
    if isinstance(value, list):
        return [_remove_jsonld_keys(item) for item in value]
    return value


def _db_row(item: dict) -> dict:
    sanitized_item = _remove_jsonld_keys(item)
    row = {
        key: value
        for key, value in sanitized_item.items()
        if isinstance(value, (int, float, bool, str, type(None)))
    }
    row["_text"] = json.dumps(sanitized_item, ensure_ascii=False)
    return row


def _openapi_path(folder: Path, key_concept: str) -> Path:
    candidates = (
        folder / f"{key_concept}.oas3.yaml",
        folder / f"{key_concept}-oas3.yaml",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No OpenAPI file found for {key_concept} in {folder}"
    )


def add_data_to_db(folder: Path, db_url: str, repository: VocabularyRepository):
    """
    Add data from the given folder to the database at the given URL.
    The db_url is a sqlite URL where every vocabulary
    is stored in a different table named after the vocabulary UUID hash.
    The UUID is the sha256 hash of ``agency_id|key_concept``.
    The _metadata table contains the full openapi specification
    as a text field containing a JSON String.
    When adding a vocabulary in the _metadata table, the
    pre-existing row is replaced with the new one.
    When adding data to other tables, the pre-existing table is dropped and re-created with the new data.

    The folder is expected to contain:
    - *.data.yamlld files with the data to be published by the API
    - *.frame.yamlld files with the framing context to be used for the API
    - openapi.yaml files with the OpenAPI specification to be used for the API
    """
    key_concept = repository.key_concept

    openapi_path = _openapi_path(folder, key_concept)
    data_path = folder / f"{key_concept}.data.yamlld"
    openapi = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
    data_payload: JsonLD = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    rows = [_db_row(item) for item in data_payload.get("@graph", [])]

    db = APIDatabase(_sqlite_path(db_url))
    with db:
        db.create_metadata_table()
        db.upsert_metadata(
            vocabulary_uri=repository.vocabulary_uri,
            agency_id=repository.agency_id,
            key_concept=repository.key_concept,
            openapi=openapi,
        )
        db.update_vocabulary_table(
            agency_id=repository.agency_id,
            key_concept=repository.key_concept,
            rows=rows,
        )


def test_add_data_to_db(tmp_path: Path):
    repository = ATECO
    collect_data(repository, tmp_path)

    db_url = f"sqlite:///{(tmp_path / 'harvest.db').as_posix()}"
    add_data_to_db(folder=tmp_path, db_url=db_url, repository=repository)
    with sqlite3.connect(_sqlite_path(db_url)) as conn:
        metadata_df: pd.DataFrame = pd.read_sql(
            "SELECT vocabulary_uuid, vocabulary_uri, agency_id, key_concept, openapi FROM _metadata",
            conn,
        )
        vocabulary_df: pd.DataFrame = pd.read_sql(
            f'SELECT id, url, _text FROM "{repository.vocabulary_uuid}" LIMIT 5',
            conn,
        )

    for _, row in metadata_df.iterrows():
        for column in [
            "vocabulary_uuid",
            "vocabulary_uri",
            "agency_id",
            "key_concept",
            "openapi",
        ]:
            assert column in row, f"Column {column} missing in metadata"
            assert row[column] is not None, (
                f"Column {column} is None in metadata"
            )

    assert not vocabulary_df.empty, "Vocabulary table is empty"
    for _, row in vocabulary_df.iterrows():
        for column in ["id", "url", "_text"]:
            assert column in row, f"Column {column} missing in vocabulary table"
            assert row[column] is not None, (
                f"Column {column} is None in vocabulary table"
            )


def test_harvest_path():
    """
    Iterate through the SNAPSHOTS directory
    and add all the vocabularies to the database.

    Don't use the sparql query to get data.
    Openapi files are not openapi.yaml but oas3.yaml.
    """
    db_url = SQLITE_URL
    snapshot_dirs = sorted(
        directory
        for directory in SNAPSHOTS.iterdir()
        if directory.is_dir() and directory.name in SNAPSHOT_REPOSITORIES
    )

    assert snapshot_dirs, "No snapshot directories found for harvesting"

    for snapshot_dir in snapshot_dirs:
        repository = SNAPSHOT_REPOSITORIES[snapshot_dir.name]
        add_data_to_db(
            folder=snapshot_dir, db_url=db_url, repository=repository
        )

    with sqlite3.connect(_sqlite_path(db_url)) as conn:
        metadata_df: pd.DataFrame = pd.read_sql(
            "SELECT vocabulary_uuid, vocabulary_uri, agency_id, key_concept FROM _metadata ORDER BY key_concept",
            conn,
        )

        assert len(metadata_df) == len(snapshot_dirs)
        assert set(metadata_df["key_concept"]) == {
            directory.name for directory in snapshot_dirs
        }

        for snapshot_dir in snapshot_dirs:
            repository = SNAPSHOT_REPOSITORIES[snapshot_dir.name]
            table_name = repository.vocabulary_uuid
            row_count = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            assert row_count > 0, (
                f"Vocabulary table is empty for {snapshot_dir.name}"
            )
