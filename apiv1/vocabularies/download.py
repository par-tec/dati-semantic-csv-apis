"""
Data loading utilities for the Vocabulary Data API.

This module provides functions for loading and transforming vocabulary data
from YAML files.
"""

import logging
from typing import Any

log = logging.getLogger(__name__)


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
            # API_BASE_URL will be injected during loading
            item["href"] = f"{{API_BASE_URL}}/{item['id']}"

        # Add href to parent items by extracting ID from their url
        if "parent" in item and isinstance(item["parent"], list):
            for parent in item["parent"]:
                if isinstance(parent, dict) and "url" in parent:
                    parent_id = parent["url"].rstrip("/").split("/")[-1]
                    parent["href"] = f"{{API_BASE_URL}}/{parent_id}"

        return item
    elif isinstance(obj, list):
        return [_transform_item(item) for item in obj]
    else:
        return obj
