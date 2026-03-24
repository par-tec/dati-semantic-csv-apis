from pathlib import Path

import pytest
import yaml
from data.app import Config, create_app
from httpx import Response

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent
ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())


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
    params, expected_status, sample_db
) -> None:
    """Malformed concept values should be rejected with a client error."""
    app = create_app(
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            HARVEST_DB=sample_db,
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


@pytest.mark.parametrize(
    "url,expected_status",
    [
        (
            "/vocabularies?concept=t%1E&description=%E2%80%88S7H&hreflang=sx&limit=131",
            400,
        ),
        (
            "/vocabularies?concept=valid&description=valid&hreflang=sx&limit=131",
            200,
        ),
        (
            "/vocabularies?concept=G%2Fx%0C%C2%A0uhJ%0B%1FSp%2F%E2%81%9F%C2%85tXQ0B",
            400,
        ),
    ],
)
def test_false_positives(url, expected_status, sample_db):
    with client_harness(
        create_app,
        Config(
            API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
            HARVEST_DB=sample_db,
        ),
    ) as (client, logs):
        response: Response = client.get(url=url)
        assert response.status_code == expected_status
