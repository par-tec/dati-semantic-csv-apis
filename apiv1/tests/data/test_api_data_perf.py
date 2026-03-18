"""Minimal performance benchmark for the OpenAPI spec endpoint."""

import json
import sqlite3

import pytest
from data.app import Config, create_app

from harvest_db_schema import (
    CREATE_METADATA_TABLE_SQL,
    CREATE_METADATA_UNIQUE_INDEX_SQL,
)
from tests.harness import client_harness

pytestmark = pytest.mark.performance


@pytest.fixture
def harvest_db(tmp_path):
    """Create a minimal harvest.db with one vocabulary spec entry."""
    db_path = tmp_path / "harvest.db"
    conn = sqlite3.connect(db_path)
    conn.execute(CREATE_METADATA_TABLE_SQL)
    conn.execute(CREATE_METADATA_UNIQUE_INDEX_SQL)
    conn.execute(
        "INSERT INTO _metadata VALUES (?, ?, ?, ?, ?)",
        (
            "test-vocab-uuid",
            "https://example.com/vocabularies/test-vocab",
            "istat",
            "test-vocab",
            json.dumps(
                {
                    "info": {
                        "title": "Test Vocabulary",
                        "version": "1.0.0",
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
            ),
        ),
    )
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.mark.skip(reason="Benchmark test, not meant for regular test runs")
def test_benchmark_show_vocabulary_spec(benchmark, harvest_db):
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE="",
            HARVEST_DB=harvest_db,
        ),
    ) as (client, _logs):
        response = benchmark(client.get, "/istat/test-vocab/openapi.yaml")

    assert response.status_code == 200
    assert "application/openapi+yaml" in response.headers["content-type"]
