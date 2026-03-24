"""Fast tests for the Vocabularies data API ASGI app."""

import json
import sqlite3
from pathlib import Path

import pytest
import yaml
from data.app import Config, create_app

from tests.harness import client_harness
from tools.store import APIStore

TESTDIR = Path(__file__).parent.parent
ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())


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


def _config(harvest_db: str) -> Config:
    return Config(
        API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
        HARVEST_DB=harvest_db,
    )


def test_get_vocabularies(single_entry_db):
    """
    When:

    - I GET /vocabularies

    Then:

    - Response contains a linkset with item: [ .. ]
    """


def test_get_single_item(single_entry_db):
    """The app should serve one known vocabulary item through the ASGI client."""
    with client_harness(create_app, _config(single_entry_db)) as (client, logs):
        response = client.get("/vocabularies/agid/test-vocab/A01")

        assert any("Application startup complete" in log for log in logs)
        assert response.status_code == 200
        assert response.json() == {
            "id": "A01",
            "label": "Item A01",
            "url": "https://example.com/vocabularies/test/A01",
            "href": "https://schema.gov.it/api/vocabularies/v1/agid/test-vocab/A01",
        }


def test_latin_header(single_entry_db):
    """Test that the API can handle latin1 headers."""
    with client_harness(
        create_app,
        _config(single_entry_db),
    ) as (client, _logs):
        response = client.get(
            "/status",
            headers={"X-Test-Header": "Café\x80"},
        )
        assert response.status_code == 200


def test_rejects_non_printable_query_parameter(single_entry_db) -> None:
    """Non-printable query parameter values should be rejected."""
    with client_harness(
        create_app,
        _config(single_entry_db),
    ) as (client, _logs):
        response = client.get(
            "/agid/test-vocab",
            params={"label": "\u2008invalid"},
        )
        assert response.status_code == 400


@pytest.mark.skip(reason="Check why it happens.")
def test_missing_vocab_returns_404(
    broken_dataset_db,
) -> None:
    """Missing vocabulary tables should be reported as a sanitized 404 problem."""
    with client_harness(
        create_app,
        _config(broken_dataset_db),
    ) as (client, _logs):
        response = client.get("/vocabularies/agid/broken-vocab")

        assert response.status_code == 404
        assert (
            response.headers["content-type"].split(";")[0]
            == "application/problem+json"
        )
        body = response.json()
        assert body["title"] == "Not Found"
        assert body["status"] == 404
        assert body["detail"] == "The requested vocabulary was not found"
