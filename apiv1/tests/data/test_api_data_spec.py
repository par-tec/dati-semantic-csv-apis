"""
Tests for the show_vocabulary_spec endpoint.
"""

import sqlite3
from pathlib import Path

import pytest
import yaml
from data.app import Config, create_app

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent

_VOCAB_OAS = {
    "info": {
        "title": "Test Vocabulary",
        "version": "1.0.0",
        "description": "A test controlled vocabulary",
    },
    "components": {
        "schemas": {
            "Item": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label_it": {"type": "string"},
                },
                "required": ["id", "label_it"],
            }
        }
    },
}


@pytest.fixture
def harvest_db(tmp_path):
    """Create a minimal harvest.db with one vocabulary entry."""
    db_path = tmp_path / "harvest.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE _metadata (agency_id TEXT, key_concept TEXT, openapi TEXT)"
    )
    conn.execute(
        "INSERT INTO _metadata VALUES (?, ?, ?)",
        ("istat", "test-vocab", yaml.dump(_VOCAB_OAS)),
    )
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def sample_db():
    return (Path(__file__).parent.parent / "harvest.db").as_posix()


def test_show_vocabulary_spec(sample_db):
    """Returns 200 with merged OAS spec in application/openapi+yaml."""
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE=str(
                TESTDIR / "api" / "agente_causale.short.yaml"
            ),
            HARVEST_DB=sample_db,
        ),
    ) as (client, _logs):
        response = client.get("/istat/ateco-2025/openapi.yaml")

        assert response.status_code == 200
        assert "application/openapi+yaml" in response.headers["content-type"]

        spec = yaml.safe_load(response.text)
        assert spec["info"]["title"] == "Test Vocabulary"
        assert "Item" in spec["components"]["schemas"]
        # The vocabulary-specific server URL should have been appended.
        server_urls = [s["url"] for s in spec.get("servers", [])]
        assert any("istat/ateco-2025" in url for url in server_urls)


def test_show_vocabulary_spec_not_found(sample_db):
    """Returns 404 when the vocabulary is not in the database."""
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE=str(
                TESTDIR / "api" / "agente_causale.short.yaml"
            ),
            HARVEST_DB=sample_db,
        ),
    ) as (client, _logs):
        response = client.get("/istat/nonexistent/openapi.yaml")

        assert response.status_code == 404
