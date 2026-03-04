"""
Tests for the Vocabularies API ASGI app.
"""

from pathlib import Path

import pytest
import schemathesis
from catalog.app import create_app
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
def test_status_endpoint_schema_compliance(case):
    """Test that the /status endpoint complies with OAS schema."""

    app = create_app()
    client = TestClient(app)

    response = client.request(
        method=case.method,
        url=case.formatted_path,
        headers=case.headers,
    )

    # Validate the response against the schema
    case.validate_response(response)
