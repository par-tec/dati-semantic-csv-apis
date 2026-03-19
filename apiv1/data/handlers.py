"""
API handlers for Controlled Vocabularies Data API.

This module provides implementations of the API endpoints
defined in openapi.yaml for serving vocabulary data items.
"""

import copy
import gzip
import json
import logging
import sqlite3
from typing import Any, cast

import yaml
from connexion import ProblemException, request
from connexion.lifecycle import ConnexionResponse

from tools.store import APIStore

log = logging.getLogger(__name__)


def _get_metadata_or_fail(
    harvest_db: APIStore,
    agency_id: str,
    key_concept: str,
) -> sqlite3.Row:
    """Return the _metadata row for (agency_id, key_concept), or None."""
    try:
        row = harvest_db.get_metadata(agency_id, key_concept)
    except sqlite3.OperationalError:
        log.exception(
            "Operational error while fetching metadata for agency_id=%s and key_concept=%s",
            agency_id,
            key_concept,
        )
        raise
    except sqlite3.DatabaseError:
        log.exception(
            "Database error while fetching metadata for agency_id=%s and key_concept=%s",
            agency_id,
            key_concept,
        )
        raise
    if not row:
        raise ProblemException(
            title="Not Found",
            status=404,
            instance=str(request.url),
        )
    assert row, "Row should be present since we checked for it above"
    return row


def _get_vocabulary_items_or_fail(
    harvest_db: APIStore,
    agency_id: str,
    key_concept: str,
) -> list[dict[str, Any]]:
    """Return the list of vocabulary items for the given vocabulary id."""
    try:
        return harvest_db.get_vocabulary_dataset(agency_id, key_concept)
    except sqlite3.OperationalError:
        log.exception(
            "Operational error while fetching vocabulary items for agency_id=%s and key_concept=%s",
            agency_id,
            key_concept,
        )
        raise
    except sqlite3.DatabaseError:
        log.exception("Database error while fetching vocabulary items")
        raise


def _query_vocabulary_items_or_fail(
    items: list[dict[str, Any]],
    limit: int = 10,
    offset: int = 0,
    cursor: str | None = None,
    label: str | None = None,
) -> list[dict[str, Any]]:
    """Return paginated vocabulary items with an optional label filter."""
    if label:
        label_lower = str(label).lower()
        items = [
            item
            for item in items
            if label_lower
            in item.get("label", item.get("label_it", "")).lower()
        ]

    if cursor:
        cursor_index = next(
            (i for i, item in enumerate(items) if item.get("id") == cursor),
            -1,
        )
        if cursor_index >= 0:
            items = items[cursor_index + 1 :]
    else:
        items = items[offset:]

    return items[:limit]


def _get_database_or_fail() -> APIStore:
    """Return the configured read-only APIStore instance."""
    harvest_db = cast(
        APIStore | None,
        getattr(request.state, "harvest_db", None),
    )
    if harvest_db is None:
        raise ValueError("Harvest DB not configured")
    return harvest_db


async def status() -> ConnexionResponse:
    """
    Health check endpoint to verify that the API is running.

    Returns:
        A ConnexionResponse with status code 200 and a simple JSON body.
    """
    return ConnexionResponse(
        status_code=200,
        content_type="application/json",
        body={"status": 200, "title": "OK"},
    )


async def show_items(
    agencyId: str,
    keyConcept: str,
    limit: int = 20,
    offset: int = 0,
    cursor: str | None = None,
    label: str | None = None,
    **kwargs: Any,
) -> ConnexionResponse:
    """
    List all vocabulary items.

    Args:
        limit: Maximum number of items to return (default: 20).
        offset: Offset for pagination (default: 0).
        cursor: Cursor for pagination (ID of the last item in previous page).
        label: Filter items by label.

    Returns:
        A tuple containing the paginated response dictionary, HTTP status code 200,
        and response headers.
    """
    assert agencyId
    assert keyConcept
    assert isinstance(limit, int)
    harvest_db = _get_database_or_fail()

    log.debug("Extra query parameters: %s", kwargs)
    all_items = _get_vocabulary_items_or_fail(harvest_db, agencyId, keyConcept)

    items = _query_vocabulary_items_or_fail(
        all_items,
        limit=limit,
        offset=offset,
        cursor=cursor,
        label=label,
    )

    response = {
        "totalResults": len(all_items),
        "limit": limit,
        "offset": offset,
        "items": items,
    }
    return ConnexionResponse(
        status_code=200,
        content_type="application/json",
        body=response,
    )


async def get_item(
    id: str,
    agencyId: str,
    keyConcept: str,
) -> ConnexionResponse:
    """
    Retrieve a single vocabulary item by its ID.

    Args:
        id: The unique identifier of the vocabulary item.

    Returns:
        A ConnexionResponse containing the item dictionary and HTTP status code,
        or a problem details object with 404 if not found.
    """
    harvest_db = _get_database_or_fail()

    item = harvest_db.get_vocabulary_item_by_id(agencyId, keyConcept, id)

    if item is None:
        # Return RFC 9457 Problem Details
        problem = {
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": f"Vocabulary item with ID '{id}' not found",
        }
        return ConnexionResponse(
            body=problem,
            status_code=404,
            content_type="application/problem+json",
        )

    return ConnexionResponse(
        status_code=200, content_type="application/json", body=item
    )


async def dump_vocabulary_dataset(
    agencyId: str, keyConcept: str
) -> ConnexionResponse:
    """
    Dump the whole dataset for the vocabulary.

    Returns:
        A ConnexionResponse containing the binary dump data, HTTP status code 200,
        and response headers.
    """
    harvest_db = _get_database_or_fail()
    vocabulary_items = _get_vocabulary_items_or_fail(
        harvest_db, agencyId, keyConcept
    )
    if not vocabulary_items:
        raise ProblemException(
            title="Not Found",
            status=404,
            instance=str(request.url),
        )

    # Create a compressed dump of the dataset
    data = {
        "items": vocabulary_items,
        "metadata": {
            "totalItems": len(vocabulary_items),
            "dumpDate": "2026-01-30T00:00:00Z",
        },
    }

    # Compress the JSON data
    json_data = json.dumps(data).encode("utf-8")
    compressed_data = gzip.compress(json_data)

    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Encoding": "gzip",
        "Content-Disposition": f'attachment; filename="vocabulary_{keyConcept}_dump.json.gz"',
    }

    return ConnexionResponse(
        status_code=200, headers=headers, body=compressed_data
    )


async def show_vocabulary_spec(
    agencyId: str, keyConcept: str
) -> ConnexionResponse:
    """
    Retrieve the OpenAPI specification for the vocabulary API
    identified by `agencyId` and `keyConcept`.

    It is obtained by merging the base OpenAPI spec with the vocabulary-specific details
    that are retrieved from a sqlite database file.

    Returns:
        A ConnexionResponse containing the OpenAPI specification in YAML format,
        HTTP status code 200, and response headers.
    """
    harvest_db = _get_database_or_fail()

    row = _get_metadata_or_fail(
        harvest_db,
        agencyId,
        keyConcept,
    )

    vocabulary_oas: dict = json.loads(row["openapi"])
    spec = copy.deepcopy(request.state.base_spec)
    spec["info"] = vocabulary_oas["info"]
    spec["components"]["schemas"]["Item"] = vocabulary_oas["components"][
        "schemas"
    ]["Item"]
    spec.setdefault("servers", []).append(
        {"url": f"{request.state.api_base_url}{agencyId}/{keyConcept}/"}
    )

    return ConnexionResponse(
        status_code=200,
        content_type="application/openapi+yaml",
        body=yaml.dump(spec),
    )
