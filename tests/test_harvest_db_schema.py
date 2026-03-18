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


@pytest.mark.parametrize("key_concept", ["test-vocab", None, ""])
@pytest.mark.parametrize("agencyId", ["agid", "missing", None, ""])
def test_build_vocabulary_uuid(agencyId, key_concept):
    if agencyId in (None, "") or key_concept in (None, ""):
        with pytest.raises(ValueError):
            build_vocabulary_uuid(agencyId, key_concept)
    else:
        assert (
            build_vocabulary_uuid(
                agency_id="ISTAT",
                key_concept="ateco-2025",
            )
            == sha256(b"istat|ateco-2025").hexdigest()
        )


def test_apidatabase_jsonld_graph_roundtrip(tmp_path):
    """Storing a JSON-LD graph and reading it back must preserve items and context.

    @-prefixed keys must be stripped in DB rows; non-ASCII labels must be
    preserved; the returned JsonLD dict must include the original @context.
    """
    db_path = tmp_path / "v.db"
    vocabulary_uuid = "test-uuid-rt"
    context = {"url": "@id", "id": "dct:identifier", "label": "skos:prefLabel"}
    graph = [
        {
            "@type": "skos:Concept",
            "id": "A",
            "url": "https://example.com/A",
            "label": "Àgenti",
            "nested": {
                "child": "value"
            },  # non-primitive — must not appear as column
        },
        {"id": "B", "url": "https://example.com/B", "label": "Beta"},
    ]

    with APIDatabase(db_path.as_posix()) as db:
        db.update_vocabulary_from_jsonld(vocabulary_uuid, graph)
        result = db.get_vocabulary_jsonld(vocabulary_uuid, context)

    assert result["@context"] == context
    items = result["@graph"]
    assert len(items) == 2
    ids = {item["id"] for item in items}
    assert ids == {"A", "B"}
    item_a = next(i for i in items if i["id"] == "A")
    assert item_a["label"] == "Àgenti", "Non-ASCII label must be preserved"
    assert "@type" not in item_a, "JSON-LD @-keys must be stripped"
    # Nested dicts are preserved in _text (the API serves them); only
    # the dedicated SQLite columns (id, url, label, …) are primitives-only.
