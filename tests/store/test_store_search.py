import pytest
import yaml

from tests.constants import DATADIR, TESTCASES
from tools.base import JsonLDFrame
from tools.openapi import Apiable
from tools.store import APIStore


@pytest.fixture
def sample_search_db(tmp_path):
    db_path = tmp_path / "harvest.db"
    base_snapshots = DATADIR / "snapshots" / "base"
    loaded_vocabularies = {}

    with APIStore(db_path.as_posix()) as db:
        db.create_metadata_table()
        for testcase in TESTCASES:
            oas3_yaml = base_snapshots / f"{testcase['name']}.oas3.yaml"
            if (
                not oas3_yaml.exists()
                or "data" not in testcase
                or "frame" not in testcase
            ):
                continue

            apiable = Apiable(testcase["data"], JsonLDFrame(testcase["frame"]))
            metadata = apiable.metadata()
            if metadata.agency_id is None or metadata.name is None:
                continue

            record_key = (metadata.agency_id, metadata.name)
            if record_key in loaded_vocabularies:
                continue

            db.upsert_metadata(
                vocabulary_uri=apiable.uri(),
                agency_id=metadata.agency_id,
                key_concept=metadata.name,
                openapi=yaml.safe_load(oas3_yaml.read_text()),
                catalog=apiable.catalog_entry(),
            )
            loaded_vocabularies[record_key] = {
                "agency_id": metadata.agency_id,
                "key_concept": metadata.name,
            }

        db.create_fts_table()

    return db_path.as_posix(), loaded_vocabularies


def test_search_metadata_matches_title(sample_search_db):
    db_path, loaded_vocabularies = sample_search_db

    with APIStore(db_path) as db:
        results = db.search_metadata("mansione")

    assert len(results) == 1
    assert results[0]["agency_id"] == "inps"
    assert results[0]["key_concept"] == "tipo_mansione_lavoratore_domestico"
    assert len(loaded_vocabularies) >= 2


def test_search_metadata_matches_description(sample_search_db):
    db_path, _ = sample_search_db

    with APIStore(db_path) as db:
        results = db.search_metadata("concausa")

    assert len(results) == 1
    assert results[0]["agency_id"] == "inail"
    assert results[0]["key_concept"] == "agente_causale"


def test_search_metadata_applies_limit(sample_search_db):
    db_path, loaded_vocabularies = sample_search_db

    with APIStore(db_path) as db:
        results = db.search_metadata("vocabolario", limit=1)

    assert len(results) == 1
    assert results[0]["key_concept"] in {
        key_concept for _, key_concept in loaded_vocabularies
    }
