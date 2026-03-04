"""
Mock handlers for Controlled Vocabularies Data API.

This module provides mock implementations of the API endpoints
defined in openapi.yaml for testing and development purposes.
"""

from pathlib import Path
from typing import Any

import yaml


def _get_api_base_url() -> str:
    """
    Extract the API base URL from the OpenAPI specification.

    Returns the first server URL from the OpenAPI spec, removing trailing slashes.

    Returns:
        The API base URL.
    """
    openapi_file = Path(__file__).parent / "openapi.yaml"
    with open(openapi_file, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    servers = spec.get("servers", [])
    if servers:
        base_url: str = servers[0].get("url", "http://localhost:8080")
        if not isinstance(base_url, str):
            raise TypeError("Server URL must be a string")
        return base_url.rstrip("/")
    return "http://localhost:8080"


# Get API base URL from OpenAPI specification
API_BASE_URL = _get_api_base_url()


def _transform_item(obj: Any) -> Any:
    """
    Recursively transform items by removing @type fields and adding href references.

    Args:
        obj: The object to transform (dict, list, or primitive).

    Returns:
        The transformed object.
    """
    if isinstance(obj, dict):
        # Remove @type field
        item = {k: _transform_item(v) for k, v in obj.items() if k != "@type"}

        # Add href to main entry using its id
        if "id" in item:
            item["href"] = f"{API_BASE_URL}/{item['id']}"

        # Add href to parent items by extracting ID from their url
        if "parent" in item and isinstance(item["parent"], list):
            for parent in item["parent"]:
                if isinstance(parent, dict) and "url" in parent:
                    parent_id = parent["url"].rstrip("/").split("/")[-1]
                    parent["href"] = f"{API_BASE_URL}/{parent_id}"

        return item
    elif isinstance(obj, list):
        return [_transform_item(item) for item in obj]
    else:
        return obj


# Load vocabulary items from the agente_causale data file
def _load_vocabulary_items() -> list[dict[str, Any]]:
    """
    Load vocabulary items from agente_causale.data.yaml.

    Returns:
        List of vocabulary items with @type field removed and href field added.
    """
    data_file = (
        Path(__file__).parent.parent.parent
        / "assets"
        / "controlled-vocabularies"
        / "agente_causale"
        / "latest"
        / "agente_causale.data.yaml"
    )

    with open(data_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Extract items from @graph and apply transformations
    return [_transform_item(item) for item in data.get("@graph", [])]


# Load the vocabulary items at module initialization
VOCABULARY_ITEMS = _load_vocabulary_items()


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
    items = VOCABULARY_ITEMS.copy()

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
        "totalResults": len(VOCABULARY_ITEMS),
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
    # Find item by ID
    item = next((item for item in VOCABULARY_ITEMS if item["id"] == id), None)

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
    # Create a mock compressed dump of the dataset
    import gzip
    import json

    data = {
        "agencyId": agencyId,
        "items": VOCABULARY_ITEMS,
        "metadata": {
            "totalItems": len(VOCABULARY_ITEMS),
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
