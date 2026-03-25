import contextlib
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import yaml
from data.app import Config
from starlette.testclient import TestClient

TESTDIR = Path(__file__).parent

ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())


def _config(harvest_db: str) -> Config:
    return Config(
        API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
        HARVEST_DB=harvest_db,
    )


@contextlib.contextmanager
def log_records() -> Iterator[list[str]]:
    """Fixture to capture log records during tests."""
    records = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    handler = ListHandler()
    logger = logging.getLogger()  # Root logger captures all logs
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield records
    logger.removeHandler(handler)


class Latin1Headers(httpx.Headers):
    """Header container that defaults to latin1 for RFC9110 compatibility tests."""

    def __init__(
        self,
        headers: Any = None,
        encoding: str = "latin1",
    ):
        if not isinstance(headers, (dict, list, type(None))):
            headers.encoding = "latin1"
        super().__init__(headers=headers, encoding="latin1")


@contextlib.contextmanager
def client_harness(
    creator: Any,
    config: Any,
) -> Iterator[tuple[TestClient, list[str]]]:
    """Fixture to create and yield the ASGI app with the given config."""
    with log_records() as logs:
        app = creator(config)
        # Patch it in this scope so all request header merges use latin1.
        with patch("httpx._models.Headers", Latin1Headers):
            with app.test_client() as client:
                client._headers.encoding = "latin1"
                yield client, logs
