"""Fast tests for the Vocabularies data API ASGI app."""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from data.app import create_app
from deepdiff import DeepDiff

from tests.harness import _config, client_harness

TESTDIR = Path(__file__).parent.parent
ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())
TESTCASES_FILE = Path(__file__).with_suffix(".yaml")
TESTCASES = cast(
    dict[str, list[dict[str, Any]]], yaml.safe_load(TESTCASES_FILE.read_text())
)


@pytest.mark.parametrize(
    "testcase",
    TESTCASES["testcases"],
    ids=[tc["name"] for tc in TESTCASES["testcases"]],
)
def test_base_requests(single_entry_db, testcase):
    """
    When:

    - I issue basic requrests

    Then:

    - I got the expected responses and logs.
    """
    with client_harness(create_app, _config(single_entry_db)) as (
        client,
        _logs,
    ):
        requests = (
            testcase["request"]
            if isinstance(testcase["request"], list)
            else [testcase["request"]]
        )
        for request in requests:
            response = client.request(
                method=request["method"],
                url=request["url"],
                headers=request.get("headers"),
                params=request.get("params"),
            )
            expected = testcase["expected"]
            assert response.status_code == expected["response"]["status_code"]
            if "json" in expected["response"]:
                diff = DeepDiff(
                    expected["response"]["json"],
                    response.json(),
                    ignore_order=True,
                )
                unexpected = {
                    key: value
                    for key, value in diff.items()
                    if not key.endswith("_added")
                }
                assert not unexpected, (
                    "Missing/changed expected JSON fields:\n"
                    + yaml.safe_dump(unexpected, sort_keys=True)
                )

            for log in expected.get("logs", []):
                assert log in _logs


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
