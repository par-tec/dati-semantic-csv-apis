"""Fast tests for the Vocabularies data API ASGI app."""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from deepdiff import DeepDiff
from vocabularies.app import create_app

from tests.harness import _config, client_harness

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

    - I issue basic requests

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

            # Then I got the expected status code ..
            assert response.status_code == expected["response"]["status_code"]

            # .. headers are as expected ..
            if expected_headers := expected["response"].get("headers"):
                for check in expected_headers:
                    present = check.get("present", True)
                    headers = {k: v for k, v in check.items() if k != "present"}
                    for header, value in headers.items():
                        if present:
                            assert header in response.headers, (
                                f"Missing expected header: {header}"
                            )
                            assert response.headers[header] == value, (
                                f"Expected header '{header}' to be '{value}', but got '{response.headers[header]}'"
                            )
                        else:
                            assert header not in response.headers, (
                                f"Unexpected header present: {header}={response.headers[header]!r}"
                            )
            # .. the content is as expected ..
            if expected_json := expected["response"].get("json"):
                diff = DeepDiff(
                    expected_json,
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

            # .. and the logs contain the expected messages.
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
