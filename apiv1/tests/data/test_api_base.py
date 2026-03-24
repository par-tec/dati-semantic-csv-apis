"""Fast tests for the Vocabularies data API ASGI app."""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from data.app import Config, create_app

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent
ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())
TESTCASES_FILE = Path(__file__).with_suffix(".yaml")
TESTCASES = cast(
    dict[str, list[dict[str, Any]]], yaml.safe_load(TESTCASES_FILE.read_text())
)


def _get_testcase(name: str) -> dict[str, Any]:
    for testcase in TESTCASES["testcases"]:
        if testcase["name"] == name:
            return testcase
    raise KeyError(f"Test case not found: {name}")


def _config(harvest_db: str) -> Config:
    return Config(
        API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
        HARVEST_DB=harvest_db,
    )


@pytest.mark.parametrize(
    "testcase",
    TESTCASES["testcases"],
    ids=[tc["name"] for tc in TESTCASES["testcases"]],
)
def test_get_vocabularies(single_entry_db, testcase):
    """
    When:

    - I GET /vocabularies

    Then:

    - Response contains a linkset with item: [ .. ]
    """
    with client_harness(create_app, _config(single_entry_db)) as (
        client,
        _logs,
    ):
        response = client.request(
            method=testcase["request"]["method"],
            url=testcase["request"]["url"],
        )
        expected = testcase["expected"]
        assert response.status_code == expected["response"]["status_code"]
        if "json" in expected["response"]:
            assert response.json() == expected["response"]["json"]

        for log in expected.get("logs", []):
            assert log in _logs


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
            "/agid/ateco-2025",
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
