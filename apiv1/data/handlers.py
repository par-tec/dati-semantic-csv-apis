"""
API handlers for Controlled Vocabularies Data API.

This module provides implementations of the API endpoints
defined in openapi.yaml for serving vocabulary data items.
"""

import gzip
import json
from typing import Any

from connexion import request


async def show_items(
    limit: int = 20,
    offset: int = 0,
    cursor: str | None = None,
    label: str | None = None,
) -> tuple[dict[str, Any], int]:
    """
    List all vocabulary items.

    Args:
        limit: Maximum number of items to return (default: 20).
        offset: Offset for pagination (default: 0).
        cursor: Cursor for pagination (ID of the last item in previous page).
        label: Filter items by label.

    Returns:
        A tuple containing the paginated response dictionary and HTTP status code 200.
    """
    # Access dataset from request state (set by lifespan handler)
    vocabulary_items = request.state.vocabulary_items
    items = vocabulary_items.copy()

    # Apply label filter if provided
    if label:
        items = [
            item for item in items if label.lower() in item["label"].lower()
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

    return response, 200


async def get_item(id: str) -> tuple[dict[str, Any], int]:
    """
    Retrieve a single vocabulary item by its ID.

    Args:
        id: The unique identifier of the vocabulary item.

    Returns:
        A tuple containing the item dictionary and HTTP status code,
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
        return problem, 404

    return item, 200


async def dump_vocabulary_dataset(
    agencyId: str,
) -> tuple[bytes, int, dict[str, str]]:
    """
    Dump the whole dataset for the vocabulary.

    Args:
        agencyId: Identifier of the vocabulary agency.

    Returns:
        A tuple containing the binary dump data, HTTP status code 200,
        and response headers.
    """
    # Access dataset from request state (set by lifespan handler)
    vocabulary_items = request.state.vocabulary_items

    # Create a compressed dump of the dataset
    data = {
        "agencyId": agencyId,
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
        "Content-Disposition": f'attachment; filename="vocabulary_{agencyId}_dump.json.gz"',
    }

    return compressed_data, 200, headers
