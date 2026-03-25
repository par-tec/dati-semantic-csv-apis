"""
Tests for the Vocabularies API ASGI app.
"""

from pathlib import Path

import pytest

# See https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/ for using schemathesis with pytest.
import schemathesis
from data.app import create_app
from httpx import Response
from hypothesis import HealthCheck, settings
from schemathesis.specs.openapi.schemas import OpenApiSchema

from tests.harness import TESTDIR, _config, client_harness

URI = "url"
APIDIR: Path = TESTDIR.parent / "data"
OPENAPI_SPEC_PATH = APIDIR / "openapi.yaml"

oas_schema: OpenApiSchema = schemathesis.openapi.from_path(
    str(OPENAPI_SPEC_PATH)
)

discover_tag = oas_schema.include(
    tag="discover-vocabularies",
)
retrieve_tag = oas_schema.include(
    tag="retrieve-data",
)
dump_tag = oas_schema.include(
    tag="dump-dataset",
)
health_tag = oas_schema.include(
    tag="health-check",
)


@discover_tag.parametrize()
@settings(
    max_examples=20,
    # verbosity=Verbosity.debug
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_openapi_compliance_discover(case, sample_db):
    return _harn_openapi_compliance(case, sample_db)


@retrieve_tag.parametrize()
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_openapi_compliance_retrieve(case, sample_db):
    return _harn_openapi_compliance(case, sample_db)


@dump_tag.parametrize()
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_openapi_compliance_dump(case, sample_db):
    return _harn_openapi_compliance(case, sample_db)


@health_tag.parametrize()
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_openapi_compliance_health(case, sample_db):
    return _harn_openapi_compliance(case, sample_db)


def _harn_openapi_compliance(case, sample_db):
    """Test that the /status endpoint complies with OAS schema."""

    with client_harness(
        create_app,
        _config(sample_db),
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
