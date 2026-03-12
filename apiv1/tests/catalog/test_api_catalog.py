"""
Tests for the Vocabularies API ASGI app.

All data validation must be performed by connexion
and not implemented manually in the handlers.
"""

from pathlib import Path

import pytest

# See https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/ for using schemathesis with pytest.
import schemathesis
from catalog.app import Config, create_app
from httpx import Response
from hypothesis import settings
from schemathesis.specs.openapi.schemas import OpenApiSchema

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent
APIDIR: Path = TESTDIR.parent / "catalog"
OPENAPI_SPEC_PATH = APIDIR / "openapi.yaml"

oas_schema: OpenApiSchema = schemathesis.openapi.from_path(
    str(OPENAPI_SPEC_PATH)
)


@oas_schema.parametrize()
@settings()
def test_openapi_compliance(case):
    """Test that the /status endpoint complies with OAS schema."""

    # When the app is initialized ...
    with client_harness(
        create_app,
        Config(
            SPARQL_URL="https://example.com/sparql",
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARIES_DATAFILE=str(
                TESTDIR / "api" / "vocabularies.linkset.yaml"
            ),
        ),
    ) as (client, logs):
        # .. the logs should indicate that the vocabularies dataset is being loaded.
        for expected_log in [
            "Loading vocabularies dataset from: ",
            "Application startup complete",
        ]:
            assert any(expected_log in log for log in logs), (
                f"Expected log message not found: {expected_log}"
            )

        # When I make a request ..
        response: Response = client.request(
            method=case.method,
            url=case.formatted_path,
            headers=case.headers,
            params=case.query,
        )

        # Then if the endpoint is not implemented ..
        # .. skip
        if response.status_code == 501:
            pytest.skip("Endpoint not implemented yet (501)")

        # .. otherwise the response should comply with the OAS schema.
        case.validate_response(response)


@pytest.mark.parametrize(
    "params,expected_status",
    [
        ({"limit": 5, "offset": 10, "author": "invalid"}, 200),
        # ({"limit": 0, "offset": 0}, 200),
        (
            {
                "limit": [1, 2, 3],
                "offset": 1000,
                "author": "https://w3id.org/italia/data/public-organization/ISTAT",
            },
            200,
        ),
        ({"limit": 1, "offset": [0, 1]}, 200),
        ({"limit": "1", "offset": [0, 1]}, 200),
        ({"limit": "1,2,3", "offset": [0, 1]}, 400),
    ],
)
def test_list_vocabularies_rejects_invalid_concept_query(
    params, expected_status
) -> None:
    """Malformed concept values should be rejected with a client error."""
    app = create_app(
        Config(
            SPARQL_URL="https://example.com/sparql",
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARIES_DATAFILE=str(
                TESTDIR / "api" / "vocabularies.linkset.yaml"
            ),
        )
    )

    with app.test_client() as client:
        response: Response = client.get(
            "/vocabularies",
            params=params,
        )

    assert response.status_code == expected_status, response.request.url
    if response.status_code == 200:
        assert (
            response.json()["linkset"][0]["limit"] == params["limit"][-1]
            if isinstance(params["limit"], list)
            else params["limit"]
        )
        assert (
            response.json()["linkset"][0]["offset"] == params["offset"][-1]
            if isinstance(params["offset"], list)
            else params["offset"]
        )
