import json
from hashlib import sha256

import pytest

from harvest_db_schema import APIDatabase, build_vocabulary_uuid


@pytest.fixture
def sample_harvest_db(tmp_path):
    db_path = tmp_path / "harvest.db"
    vocabulary_uuid = "uuid-1"

    with APIDatabase(db_path.as_posix()) as db:
        db.create_metadata_table()
        db.upsert_metadata(
            vocabulary_uuid=vocabulary_uuid,
            vocabulary_uri="https://example.com/vocabularies/test",
            agency_id="agid",
            key_concept="test-vocab",
            openapi={"openapi": "3.0.3", "paths": {}},
        )
        db.update_vocabulary_table(
            vocabulary_uuid=vocabulary_uuid,
            rows=[
                {
                    "id": "A01",
                    "label": "Item A01",
                    "_text": json.dumps({"id": "A01", "label": "Item A01"}),
                },
                {
                    "id": "A02",
                    "label": "Item A02",
                    "_text": json.dumps({"id": "A02", "label": "Item A02"}),
                },
            ],
        )

    return db_path.as_posix(), vocabulary_uuid


def test_get_vocabulary_uuid_returns_value(sample_harvest_db):
    db_path, vocabulary_uuid = sample_harvest_db
    db = APIDatabase(db_path)

    assert db.get_vocabulary_uuid("agid", "test-vocab") == vocabulary_uuid


def test_get_vocabulary_uuid_returns_none_when_missing(sample_harvest_db):
    db_path, _ = sample_harvest_db
    db = APIDatabase(db_path)

    assert db.get_vocabulary_uuid("missing", "missing") is None


def test_get_vocabulary_item_by_id_returns_item(sample_harvest_db):
    db_path, vocabulary_uuid = sample_harvest_db
    db = APIDatabase(db_path)

    assert db.get_vocabulary_item_by_id(vocabulary_uuid, "A01") == {
        "id": "A01",
        "label": "Item A01",
    }


def test_get_vocabulary_dataset_returns_items(sample_harvest_db):
    db_path, vocabulary_uuid = sample_harvest_db
    db = APIDatabase(db_path)

    assert db.get_vocabulary_dataset(vocabulary_uuid) == [
        {"id": "A01", "label": "Item A01"},
        {"id": "A02", "label": "Item A02"},
    ]


def test_build_vocabulary_uuid_prefers_agency_and_key_concept():
    assert (
        build_vocabulary_uuid(
            agency_id="ISTAT",
            key_concept="ateco-2025",
            vocabulary_uri="https://example.com/vocabularies/ignored",
        )
        == sha256(b"istat|ateco-2025").hexdigest()
    )


def test_build_vocabulary_uuid_falls_back_to_uri_hash():
    uri = "https://example.com/vocabularies/fallback"
    assert (
        build_vocabulary_uuid(
            agency_id="",
            key_concept="ateco-2025",
            vocabulary_uri=uri,
        )
        == sha256(uri.encode("utf-8")).hexdigest()
    )
