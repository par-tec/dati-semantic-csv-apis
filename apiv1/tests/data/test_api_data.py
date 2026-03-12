"""
Tests for the Vocabularies API ASGI app.
"""

from pathlib import Path

import pytest

# See https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/ for using schemathesis with pytest.
import schemathesis
from data.app import Config, create_app
from httpx import Response
from hypothesis import settings
from schemathesis.specs.openapi.schemas import OpenApiSchema

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent
APIDIR: Path = TESTDIR.parent / "data"
OPENAPI_SPEC_PATH = APIDIR / "openapi.yaml"

oas_schema: OpenApiSchema = schemathesis.openapi.from_path(
    str(OPENAPI_SPEC_PATH)
)


@oas_schema.parametrize()
@settings(
    # max_examples=50,
    # verbosity=Verbosity.debug
)
def test_openapi_compliance(case):
    """Test that the /status endpoint complies with OAS schema."""

    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE=str(
                TESTDIR / "api" / "agente_causale.short.yaml"
            ),
        ),
    ) as (client, logs):
        # .. the logs should indicate that the vocabularies dataset is being loaded.
        for expected_log in [
            # "Loaded 2922 vocabulary items",
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


def test_latin_header():
    """Test that the API can handle latin1 headers."""
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE=str(
                TESTDIR / "api" / "agente_causale.short.yaml"
            ),
        ),
    ) as (client, logs):
        response: Response = client.get(
            "/status",
            headers={"X-Test-Header": "Café\x80"},
        )
        assert response.status_code == 200
