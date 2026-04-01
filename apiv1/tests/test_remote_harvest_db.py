"""
Tests for remote harvest DB download support.

The download is performed by entrypoint.py before uvicorn starts.
These tests cover the _download_db helper used by the entrypoint.
"""

import asyncio

import pytest
from entrypoint import _download_db


@pytest.mark.parametrize(
    "url, timeout, match",
    [
        ("http://example.com/harvest.db", 10, "must use https://"),
        ("file:///etc/passwd", 10, "must use https://"),
        ("https://example.com/harvest.db", 121, "HARVEST_DB_TIMEOUT"),
    ],
)
def test_download_db_rejects_invalid_input(tmp_path, url, timeout, match):
    """_download_db raises ValueError for unsafe URLs or out-of-range timeout."""
    dest = (tmp_path / "harvest.db").as_posix()
    with pytest.raises(ValueError, match=match):
        asyncio.run(_download_db(url, dest, 1024, timeout))
