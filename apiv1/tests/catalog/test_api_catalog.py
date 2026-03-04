"""
Tests for the Vocabularies API ASGI app.
"""

import contextlib
import logging
from pathlib import Path

import pytest

# See https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/ for using schemathesis with pytest.
import schemathesis
from catalog.app import Config, create_app
from httpx import Response
from hypothesis import settings
from schemathesis.specs.openapi.schemas import OpenApiSchema

TESTDIR = Path(__file__).parent.parent
OPENAPI_SPEC_PATH = TESTDIR.parent / "catalog" / "openapi.yaml"

oas_schema: OpenApiSchema = schemathesis.openapi.from_path(
    str(OPENAPI_SPEC_PATH)
)


@contextlib.contextmanager
def log_records():
    """Fixture to capture log records during tests."""
    records = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = ListHandler()
    logger = logging.getLogger()  # Root logger captures all logs
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield records
    logger.removeHandler(handler)


@oas_schema.parametrize()
@settings()
def test_status_endpoint_schema_compliance(case):
    """Test that the /status endpoint complies with OAS schema."""

    with log_records() as logs:
        # Given the ASGI app...
        app = create_app(
            Config(
                SPARQL_URL="https://example.com/sparql",
                API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
                VOCABULARIES_DATAFILE=str(
                    TESTDIR / "api" / "vocabularies.linkset.yaml"
                ),
            )
        )
        # When the app is initialized ...
        with app.test_client() as client:
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
