"""
API handlers for vocabularies endpoint.

This module implements handlers for serving controlled vocabularies
in RFC 9727 linkset format with filtering capabilities.
"""

import json
import logging
from typing import Any

from common.utils import _get_database_or_fail
from connexion import request

from tools.store import APIStore

log = logging.getLogger(__name__)


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


def _to_catalog_item(
    item: dict[str, Any],
    api_base_url: str,
    predecessor_base_url: str,
) -> dict[str, Any] | None:
    """
    Convert a dictionary item from _metadata
    containing agency_id, key_concept, vocabulary_uri
    to a catalog_item of the form


    """
    try:
        catalog = json.loads(item["catalog"])
        vocabulary_uri = item["vocabulary_uri"]
        api_url: str = "/".join(
            (
                api_base_url,
                "vocabularies",
                item["agency_id"],
                item["key_concept"],
            )
        )
        oas_url = "/".join((api_url, "openapi.yaml"))
        pre_url = "/".join(
            (predecessor_base_url, item["agency_id"], item["key_concept"])
        )
        return {
            "href": api_url,
            "about": vocabulary_uri,
            "title": catalog["title"],
            "description": catalog["description"],
            "hreflang": catalog["hreflang"],
            # "type": "application/json",
            "version": catalog["version"],
            "author": catalog["author"],
            "service-desc": [
                {"href": oas_url, "type": "application/openapi+yaml"}
            ],
            "service-meta": [
                {
                    "href": f"{vocabulary_uri}?output=application/ld+json",
                    "type": "application/ld+json",
                }
            ],
            "predecessor-version": [
                {
                    "href": pre_url,
                }
            ],
        }
    except (KeyError, json.JSONDecodeError) as e:
        log.exception(
            f"Skipping invalid catalog entry in database for agency_id={item['agency_id']} "
            f"and key_concept={item['key_concept']}: {e}"
        )
        return None


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

    rows = db.search_metadata(query=description, limit=limit, offset=offset)

    items: list[dict[str, Any]] = [
        item
        for x in rows
        if (
            item := _to_catalog_item(
                x, request.state.api_base_url, "https://old.example.com"
            )
        )
        is not None
    ]
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
                "anchor": request.state.api_base_url,
                "api-catalog": request.state.api_base_url,
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
