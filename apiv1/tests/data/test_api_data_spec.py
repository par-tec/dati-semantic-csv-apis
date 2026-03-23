"""
Tests for the show_vocabulary_spec endpoint.
"""

import json
import sqlite3
from pathlib import Path

import pytest
import yaml
from data.app import Config, create_app

from tests.harness import client_harness
from tools.store import (
    APIStore,
)

TESTDIR = Path(__file__).parent.parent

ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())


@pytest.fixture
def harvest_db(tmp_path):
    """Create a minimal harvest.db with one vocabulary entry."""
    db_path = tmp_path / "harvest.db"
    conn = sqlite3.connect(db_path)
    store = APIStore(db_path.as_posix())
    store.create_metadata_table()
    conn.execute(
        "INSERT INTO _metadata VALUES (:vocabulary_uuid, :vocabulary_uri, :agency_id, :key_concept, :openapi, :catalog)",
        {
            "vocabulary_uuid": "ateco-2025-uuid",
            "vocabulary_uri": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
            "agency_id": "istat",
            "key_concept": "ateco-2025",
            "openapi": json.dumps(ATECO_SPEC),
            "catalog": json.dumps(
                {
                    "about": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
                    "author": "https://w3id.org/italia/data/public-organization/ISTAT",
                    "href": "https://schema.gov.it/api/vocabularies/v1/istat/ateco-2025",
                    "hreflang": ["it"],
                    "service-desc": [
                        {
                            "href": "/istat/ateco-2025/openapi.yaml",
                            "type": "application/openapi+yaml",
                        }
                    ],
                    "service-meta": [
                        {
                            "href": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025?output=application/ld+json",
                            "type": "application/ld+json",
                        }
                    ],
                    "title": "Classificazione Ateco 2025",
                    "version": "versione 2025",
                }
            ),
        },
    )
    conn.commit()
    conn.close()
    return str(db_path)


def test_show_vocabulary_spec(harvest_db):
    """Returns 200 with merged OAS spec in application/openapi+yaml."""
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE="",
            HARVEST_DB=harvest_db,
        ),
    ) as (client, _logs):
        response = client.get("/vocabularies/istat/ateco-2025/openapi.yaml")

        assert response.status_code == 200
        assert "application/openapi+yaml" in response.headers["content-type"]

        spec = yaml.safe_load(response.text)
        assert spec["info"]["title"] == ATECO_SPEC["info"]["title"]
        assert (
            spec["components"]["schemas"]["Item"]
            == ATECO_SPEC["components"]["schemas"]["Item"]
        )
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
        response = client.get("/vocabularies/istat/nonexistent/openapi.yaml")

        assert response.status_code == 404
