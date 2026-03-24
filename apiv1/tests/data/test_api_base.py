"""Fast tests for the Vocabularies data API ASGI app."""

from pathlib import Path

import pytest
import yaml
from data.app import Config, create_app

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent
ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())


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
    with client_harness(create_app, _config(single_entry_db)) as (client, logs):
        response = client.get("/vocabularies")
        assert response.json() == {
            "linkset": [
                {
                    "anchor": "https://schema.gov.it/api/vocabularies/v1",
                    "api-catalog": "https://schema.gov.it/api/vocabularies/v1/agid/test-vocab/openapi.yaml",
                    "count": 0,
                    "item": [],
                    "limit": 20,
                    "offset": 0,
                    "total_count": 0,
                }
            ]
        }
        raise NotImplementedError


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
