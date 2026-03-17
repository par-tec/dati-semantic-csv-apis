"""
Tests for the Vocabularies API ASGI app.
"""

from pathlib import Path

import pytest

# See https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/ for using schemathesis with pytest.
import schemathesis
from data.app import Config, create_app
from httpx import Response
from hypothesis import HealthCheck, settings
from schemathesis.specs.openapi.schemas import OpenApiSchema

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent
APIDIR: Path = TESTDIR.parent / "data"
OPENAPI_SPEC_PATH = APIDIR / "openapi.yaml"

oas_schema: OpenApiSchema = schemathesis.openapi.from_path(
    str(OPENAPI_SPEC_PATH)
)


@oas_schema.include(
    operation_id="data.handlers.dump_vocabulary_dataset"
).parametrize()
@settings(
    max_examples=50,
    # verbosity=Verbosity.debug
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_openapi_compliance(case, sample_db):
    """Test that the /status endpoint complies with OAS schema."""

    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE="",
            HARVEST_DB=sample_db,
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


def test_latin_header(sample_db):
    """Test that the API can handle latin1 headers."""
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE="",
            HARVEST_DB=sample_db,
        ),
    ) as (client, logs):
        response: Response = client.get(
            "/status",
            headers={"X-Test-Header": "Café\x80"},
        )
        assert response.status_code == 200


def test_rejects_non_printable_query_parameter(sample_db) -> None:
    """Non-printable query parameter values should be rejected."""
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            VOCABULARY_DATAFILE="",
            HARVEST_DB=sample_db,
        ),
    ) as (client, logs):
        response: Response = client.get(
            "/",
            params={"label": "\u2008invalid"},
        )
        assert response.status_code == 400
