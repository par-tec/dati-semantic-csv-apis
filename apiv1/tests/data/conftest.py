import json
import sqlite3
from pathlib import Path

import pytest
import yaml

from tools.store import APIStore

TESTDIR = Path(__file__).parent.parent
ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())


TESTDIR = Path(__file__).parent.parent
DATADIR = TESTDIR / "data"


@pytest.fixture
def sample_db():
    return (DATADIR / "aggregate.db").as_posix()


@pytest.fixture
def single_entry_db(tmp_path: Path) -> str:
    db_path = tmp_path / "deleteme.db"

    with APIStore(db_path.as_posix()) as db:
        db.create_metadata_table()
        db.upsert_metadata(
            vocabulary_uri="https://example.com/vocabularies/test",
            agency_id="agid",
            key_concept="test-vocab",
            openapi=ATECO_SPEC,
            catalog={
                "about": "https://example.com/vocabularies/test",
                "hreflang": ["en"],
                "title": "Test Vocabulary",
                "type": "API Catalog",
                "href": "https://example.com/vocabularies/test",
            },
        )
        db.update_vocabulary_table(
            agency_id="agid",
            key_concept="test-vocab",
            rows=[
                {
                    "id": "A01",
                    "url": "https://example.com/vocabularies/test/A01",
                    "label": "Item A01",
                    "level": "1",
                    "_text": json.dumps(
                        {
                            "id": "A01",
                            "label": "Item A01",
                            "url": "https://example.com/vocabularies/test/A01",
                        }
                    ),
                }
            ],
        )

    return db_path.as_posix()


@pytest.fixture
def broken_dataset_db(tmp_path: Path) -> str:
    db_path = tmp_path / "broken-harvest.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE _metadata (
            vocabulary_uuid TEXT PRIMARY KEY,
            vocabulary_uri TEXT NOT NULL,
            agency_id TEXT NOT NULL,
            key_concept TEXT NOT NULL,
            openapi TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX agency_id_key_concept_unique
        ON _metadata (agency_id, key_concept)
        """
    )
    conn.execute(
        "INSERT INTO _metadata VALUES (?, ?, ?, ?, ?)",
        (
            "missing-table-uuid",
            "https://example.com/vocabularies/broken",
            "agid",
            "broken-vocab",
            json.dumps(ATECO_SPEC),
        ),
    )
    conn.commit()
    conn.close()
    return db_path.as_posix()
