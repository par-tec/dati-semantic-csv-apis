"""
Tests for the Vocabularies API ASGI app.
"""

import logging
from pathlib import Path

import pytest

# See https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/ for using schemathesis with pytest.
import schemathesis
from catalog.app import Config, create_app
from hypothesis import settings
from starlette.testclient import TestClient

TESTDIR = Path(__file__).parent.parent
OPENAPI_SPEC_PATH = TESTDIR.parent / "catalog" / "openapi.yaml"


@pytest.fixture(scope="function")
def app():
    """Create an app instance for testing."""
    return create_app()


@pytest.fixture(scope="function")
def client(app) -> TestClient:
    """Create a test client for the ASGI app."""
    return TestClient(app)


# Load OAS schema for schemathesis validation
oas_schema = schemathesis.openapi.from_path(str(OPENAPI_SPEC_PATH))


@oas_schema.parametrize()
@settings(max_examples=10)
def test_status_endpoint_schema_compliance(case):
    """Test that the /status endpoint complies with OAS schema."""

    # Capture logs manually (resets between Hypothesis inputs)
    log_records = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            log_records.append(record)

    handler = ListHandler()
    logger = logging.getLogger()  # Root logger captures all logs
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        app = create_app(
            Config(
                SPARQL_URL="https://example.com/sparql",
                API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
                VOCABULARIES_DATAFILE=str(
                    TESTDIR / "api" / "vocabularies.linkset.yaml"
                ),
            )
        )

        # Use TestClient as context manager to trigger lifespan events
        with TestClient(app) as client:
            response = client.request(
                method=case.method,
                url=case.formatted_path,
                headers=case.headers,
            )

            # Skip test if endpoint returns 501 (Not Implemented)
            if response.status_code == 501:
                pytest.skip("Endpoint not implemented yet (501)")

            # Validate the response against the schema
            case.validate_response(response)

            # Access logs via log_records
            # Example: assert any("Application startup" in record.getMessage() for record in log_records)

    finally:
        logger.removeHandler(handler)
