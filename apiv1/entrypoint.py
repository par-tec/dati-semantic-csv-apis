"""
Download harvest DB if HARVEST_DB is an https:// URL, then exec uvicorn.

Usage (via Dockerfile ENTRYPOINT):
    python /app/entrypoint.py vocabularies.asgi:application --host 0.0.0.0 --port 8080
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx

from tools.store import APIStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

harvest_db = os.environ.get("HARVEST_DB", "harvest.db")
max_size = int(os.environ.get("HARVEST_DB_MAX_SIZE", 100 * 1024 * 1024))
timeout = int(os.environ.get("HARVEST_DB_TIMEOUT", 30))


async def _download_db(
    url: str, dest_path: str, max_size: int, timeout: int
) -> None:
    """Download the harvest DB from a remote URL, enforcing a maximum file size.

    Only https:// URLs are accepted. Raises ValueError if the download exceeds
    max_size bytes, the URL scheme is not https, or timeout exceeds 120 seconds.
    """
    if not url.startswith("https://"):
        raise ValueError(f"HARVEST_DB_URL must use https://, got: {url!r}")
    if timeout > 120:
        raise ValueError(
            f"HARVEST_DB_TIMEOUT must be <= 120 seconds, got: {timeout}"
        )
    logger.info("Downloading harvest DB from %s to %s", url, dest_path)
    downloaded = 0
    async with httpx.AsyncClient(
        follow_redirects=False, timeout=httpx.Timeout(timeout)
    ) as client:
        async with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise ValueError(
                    f"Failed to download harvest DB from {url}: "
                    f"HTTP {response.status_code}. "
                    f"Only direct 200 OK responses are accepted to avoid downloading HTML error pages, "
                    f"while redirects are not followed to prevent downloading from unintended locations. "
                    f"Ensure the URL points directly to the .db file and is accessible without redirects."
                )
            with open(dest_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                    downloaded += len(chunk)
                    if downloaded > max_size:
                        raise ValueError(
                            f"Download from {url} exceeded maximum allowed size"
                            f" of {max_size} bytes"
                        )
                    f.write(chunk)
    logger.info("Downloaded %d bytes to %s", downloaded, dest_path)


def _validate_db(harvest_db: str) -> None:
    """Validate that the datastore file exists and has the expected structure."""
    try:
        with APIStore(harvest_db, read_only=True) as db:
            db.validate_metadata_schema()
            db.validate_metadata_content()
    except Exception as e:
        logger.error(
            "Error validating datastore %s: %s", Path(harvest_db).absolute(), e
        )
        raise ValueError(f"Invalid datastore {harvest_db}: {e}") from e


if __name__ == "__main__":
    if harvest_db.startswith("https://"):
        local_path = Path(harvest_db).name
        logger.info("Downloading harvest DB from %s", harvest_db)
        asyncio.run(_download_db(harvest_db, local_path, max_size, timeout))
        os.environ["HARVEST_DB"] = local_path
        logger.info("Download complete, validating the downloaded DB")
    else:
        logger.info("Using local harvest DB at %s", harvest_db)
        local_path = harvest_db

    _validate_db(harvest_db=local_path)
    logger.info("DB validation successful")

    os.execvp("uvicorn", ["uvicorn"] + sys.argv[1:])
