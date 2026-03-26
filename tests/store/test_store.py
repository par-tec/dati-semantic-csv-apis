import json
from hashlib import sha256

import pytest

from tools.store import APIStore, build_vocabulary_uuid


@pytest.fixture
def sample_harvest_db(tmp_path):
    db_path = tmp_path / "harvest.db"
    agency_id = "agid"
    key_concept = "ateco-2025"

    with APIStore(db_path.as_posix()) as db:
        db.create_metadata_table()
        db.upsert_metadata(
            vocabulary_uri="https://example.com/vocabularies/test",
            agency_id=agency_id,
            key_concept=key_concept,
            openapi={"openapi": "3.0.3", "paths": {}},
            catalog={},
        )
        db.update_vocabulary_table(
            agency_id=agency_id,
            key_concept=key_concept,
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

    return db_path.as_posix(), agency_id, key_concept


def test_get_vocabulary_item_by_id_returns_item(sample_harvest_db):
    db_path, agency_id, key_concept = sample_harvest_db
    db = APIStore(db_path)

    assert db.get_vocabulary_item_by_id(agency_id, key_concept, "A01") == {
        "id": "A01",
        "label": "Item A01",
    }


def test_get_vocabulary_dataset_returns_items(sample_harvest_db):
    db_path, agency_id, key_concept = sample_harvest_db
    db = APIStore(db_path)

    assert db.get_vocabulary_dataset(agency_id, key_concept) == [
        {"id": "A01", "label": "Item A01"},
        {"id": "A02", "label": "Item A02"},
    ]


@pytest.mark.parametrize(
    "testcase",
    [
        {
            "params": {},
            "expected": [
                {"id": "A01", "label": "Item A01"},
                {"id": "A02", "label": "Item A02"},
            ],
        },
        {
            "params": {"limit": 1},
            "expected": [{"id": "A01", "label": "Item A01"}],
        },
        {
            "params": {"limit": "1", "cursor": "A01"},
            "expected": [{"id": "A02", "label": "Item A02"}],
        },
        {
            "params": {},
            "expected": [
                {"id": "A01", "label": "Item A01"},
                {"id": "A02", "label": "Item A02"},
            ],
        },
    ],
)
def test_get_vocabulary_dataset_with_limit(sample_harvest_db, testcase):
    db_path, agency_id, key_concept = sample_harvest_db
    db = APIStore(db_path)

    assert (
        db.get_vocabulary_dataset(
            agency_id, key_concept, params=testcase["params"]
        )
        == testcase["expected"]
    )


@pytest.mark.parametrize("key_concept", ["ateco-2025", None, ""])
@pytest.mark.parametrize("agencyId", ["agid", "missing", None, ""])
def test_build_vocabulary_uuid(agencyId, key_concept):
    if agencyId in (None, "") or key_concept in (None, ""):
        with pytest.raises((ValueError, AssertionError)):
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
    agency_id = "agid"
    key_concept = "test-uuid-rt"
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

    with APIStore(db_path.as_posix()) as db:
        db.update_vocabulary_from_jsonld(agency_id, key_concept, graph)
        result = db.get_vocabulary_jsonld(agency_id, key_concept, context)

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


def test_upsert_metadata_preserves_openapi_when_empty_dict(tmp_path):
    db_path = tmp_path / "deleteme.db"

    with APIStore(db_path.as_posix()) as db:
        db.create_metadata_table()
        db.upsert_metadata(
            vocabulary_uri="https://example.com/vocabularies/test-v1",
            agency_id="agid",
            key_concept="ateco-2025",
            openapi={"openapi": "3.0.3", "info": {"title": "Original"}},
            catalog={
                "version": "1",
                "title": "Test Catalog",
                "description": "A test catalog",
                "hreflang": ["en"],
                "author": "https://example.com/author",
            },
        )

        db.upsert_metadata(
            vocabulary_uri="https://example.com/vocabularies/test-v2",
            agency_id="agid",
            key_concept="ateco-2025",
            openapi={},
            catalog={
                "version": "2",
                "title": "Test Catalog",
                "description": "A test catalog",
                "hreflang": ["en"],
                "author": "https://example.com/author",
            },
        )

        metadata = db.get_metadata("agid", "ateco-2025")

        assert (
            metadata["vocabulary_uri"]
            == "https://example.com/vocabularies/test-v2"
        )
        assert json.loads(metadata["openapi"]) == {
            "openapi": "3.0.3",
            "info": {"title": "Original"},
        }
        assert json.loads(metadata["catalog"])["version"] == "2"
        db.upsert_metadata(
            vocabulary_uri="https://example.com/vocabularies/test-v2",
            agency_id="agid",
            key_concept="ateco-2025",
            openapi={"openapi": "3.0.4", "info": {"title": "Original"}},
            catalog={},
        )

        metadata = db.get_metadata("agid", "ateco-2025")
        assert json.loads(metadata["openapi"]) == {
            "openapi": "3.0.4",
            "info": {"title": "Original"},
        }
        assert json.loads(metadata["catalog"])["version"] == "2"
