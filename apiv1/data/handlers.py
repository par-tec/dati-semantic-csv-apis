"""
API handlers for Controlled Vocabularies Data API.

This module provides implementations of the API endpoints
defined in openapi.yaml for serving vocabulary data items.
"""

import copy
import gzip
import json
import logging
from typing import Any

import yaml
from connexion import request
from connexion.lifecycle import ConnexionResponse

from .errors import safe_problem

log = logging.getLogger(__name__)


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
    assert isinstance(limit, int)

    log.debug("Extra query parameters: %s", kwargs)
    # Access dataset from request state (set by lifespan handler)
    vocabulary_items = request.state.vocabulary_items
    items = vocabulary_items.copy()

    # Apply label filter if provided
    if label:
        items = [
            item
            for item in items
            if label.lower() in item.get("label", item["label_it"]).lower()
        ]

    # Apply cursor-based pagination if cursor is provided
    if cursor:
        # Find the index of the cursor item
        cursor_index = next(
            (i for i, item in enumerate(items) if item["id"] == cursor), -1
        )
        if cursor_index >= 0:
            items = items[cursor_index + 1 :]
    else:
        # Apply offset-based pagination
        items = items[offset:]

    # Apply limit
    items = items[:limit]

    response = {
        "totalResults": len(vocabulary_items),
        "limit": limit,
        "offset": offset,
        "items": items,
    }
    return ConnexionResponse(
        status_code=200,
        content_type="application/json",
        body=response,
    )


async def get_item(id: str) -> ConnexionResponse:
    """
    Retrieve a single vocabulary item by its ID.

    Args:
        id: The unique identifier of the vocabulary item.

    Returns:
        A ConnexionResponse containing the item dictionary and HTTP status code,
        or a problem details object with 404 if not found.
    """
    # Access dataset from request state (set by lifespan handler)
    vocabulary_items = request.state.vocabulary_items

    # Find item by ID
    item = next((item for item in vocabulary_items if item["id"] == id), None)

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


async def dump_vocabulary_dataset() -> ConnexionResponse:
    """
    Dump the whole dataset for the vocabulary.

    Returns:
        A ConnexionResponse containing the binary dump data, HTTP status code 200,
        and response headers.
    """
    keyConcept = "agente_causale"
    # raise NotImplementedError("Dump endpoint not implemented yet")
    # Access dataset from request state (set by lifespan handler)
    vocabulary_items = request.state.vocabulary_items

    # Create a compressed dump of the dataset
    data = {
        "items": vocabulary_items,
        "metadata": {
            "totalItems": len(vocabulary_items),
            "dumpDate": "2026-01-30T00:00:00Z",
        },
    }

    # Compress the JSON data
    json_data = json.dumps(data, indent=2).encode("utf-8")
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
    # Open the sqlite database and retrieve the OAS spec from the _metadata table.
    query = """SELECT openapi FROM _metadata WHERE agency_id = ? AND key_concept = ?"""
    breakpoint()
    db_connection = request.state.db_connection
    if db_connection is None:
        raise NotImplementedError("Harvest DB not configured")

    cursor = db_connection.execute(query, (agencyId, keyConcept))
    row = cursor.fetchone()

    if row is None:
        return safe_problem(
            title="Not Found",
            status=404,
            instance=str(request.url),
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
