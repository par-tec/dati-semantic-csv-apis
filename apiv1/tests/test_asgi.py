"""
Minimal smoke tests for the ASGI entry point.

Given a valid harvest DB,
  the ASGI application responds correctly on basic endpoints.
"""

from starlette.testclient import TestClient
from vocabularies.app import create_app

from tests.harness import _config


def test_status(single_entry_db):
    """Given a valid harvest DB, /status returns 200."""
    app = create_app(config=_config(single_entry_db))
    with TestClient(app) as client:
        resp = client.get("/status")
    assert resp.status_code == 200


def test_cache_control_header(single_entry_db):
    """Given a valid harvest DB, responses include a Cache-Control header."""
    app = create_app(config=_config(single_entry_db))
    with TestClient(app) as client:
        resp = client.get("/status")
    assert "cache-control" in resp.headers
