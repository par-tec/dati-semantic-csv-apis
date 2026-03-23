"""
API handlers for vocabularies endpoint.

This module implements handlers for serving controlled vocabularies
in RFC 9727 linkset format with filtering capabilities.
"""

from typing import Any

from common.utils import _get_database_or_fail
from connexion import request

from tools.store import APIStore


def filter_vocabularies(
    items: list[dict[str, Any]],
    author: str | None = None,
    hreflang: str | None = None,
    concept: str | None = None,
    type_: str | None = None,
    title: str | None = None,
    description: str | None = None,
):
    """
    Filter vocabulary items based on provided criteria.

    Args:
        items: list of linkset items to filter.
        author: Filter by author URI.
        hreflang: Filter by language code (must be present in hreflang array).
        concept: Filter by concept identifier (_concept field).
        type_: Filter by vocabulary type URI (_vocabulary_type field).

    Yields:
        Filtered linkset items.
    """
    for item in items:
        if title and title.lower() not in item.get("title", "").lower():
            continue
        if (
            description
            and description.lower() not in item.get("description", "").lower()
        ):
            continue
        if author and item.get("author") != author:
            continue
        if hreflang and hreflang not in item.get("hreflang", []):
            continue
        if concept and item.get("_concept") != concept:
            continue
        if type_ and item.get("_vocabulary_type") != type_:
            continue
        yield item


def get_status():
    """
    Get the status of the API.
    """
    return (
        {
            "status": 200,
            "title": "Vocabularies API is running",
            "type": "about:blank",
        },
        200,
        {"Content-Type": "application/json"},
    )


def list_vocabularies_by_agency(
    agencyId: str,
) -> tuple[dict[str, Any], int, dict[str, str]]:
    raise NotImplementedError("This endpoint is not implemented yet.")


def list_vocabularies(
    title: str | None = None,
    description: str | None = None,
    author: str | None = None,
    hreflang: str | None = None,
    concept: str | None = None,
    type: str | None = None,
    limit: int = 10,
    offset: int = 0,
    **kwargs: Any,
) -> tuple[dict[str, Any], int, dict[str, str]]:
    """
    Get vocabularies with optional filtering.

    This handler loads the vocabularies linkset and applies filters
    based on the query parameters.

    Args:
        author: Filter by author URI.
        hreflang: Filter by language code.
        concept: Filter by concept identifier.
        type: Filter by vocabulary type URI.
        limit: Maximum number of items to return.
        offset: Number of items to skip before starting to collect the result set.

    Returns:
        Linkset dictionary with filtered items.
    """
    if kwargs:
        raise ValueError(f"Unexpected query parameters: {kwargs}")

    db: APIStore = _get_database_or_fail()

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT agency_id, key_concept, catalog, openapi FROM _metadata"
        ).fetchall()
        linkset_data = {
            "linkset": [
                {
                    "anchor": request.state.api_base_url.rstrip("/"),
                    "api-catalog": "/".join(
                        [
                            request.state.api_base_url.rstrip("/"),
                            row["agency_id"],
                            row["key_concept"],
                            "openapi.yaml",
                        ]
                    ),
                    "item": [],
                }
                for row in rows
            ]
        }

    catalog = linkset_data["linkset"][0]
    items = catalog.get("item", [])

    # Apply filters
    filtered_items = list(
        filter_vocabularies(
            items,
            author=author,
            hreflang=hreflang,
            concept=concept,
            type_=type,
            title=title,
            description=description,
        )
    )

    # Reconstruct linkset with filtered items
    result = {
        "linkset": [
            {
                "anchor": catalog["anchor"],
                "api-catalog": catalog["api-catalog"],
                "item": filtered_items[offset : offset + limit],
                # Pagination metadata.
                "total_count": len(filtered_items),
                "count": len(filtered_items[offset : offset + limit]),
                "limit": limit,
                "offset": offset,
            }
        ]
    }

    return result, 200, {"Content-Type": "application/linkset+json"}
