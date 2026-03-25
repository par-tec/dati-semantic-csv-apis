"""
Tests for the show_vocabulary_spec endpoint.
"""

import yaml
from vocabularies.app import create_app

from tests.harness import ATECO_SPEC, _config, client_harness


def test_show_vocabulary_spec(single_entry_db):
    """Returns 200 with merged OAS spec in application/openapi+yaml."""
    with client_harness(
        create_app,
        _config(single_entry_db),
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


def test_show_vocabulary_spec_not_found(single_entry_db):
    """Returns 404 when the vocabulary is not in the database."""
    with client_harness(
        create_app,
        _config(single_entry_db),
    ) as (client, _logs):
        response = client.get("/vocabularies/istat/nonexistent/openapi.yaml")

        assert response.status_code == 404
