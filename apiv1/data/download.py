"""
Data loading utilities for the Vocabulary Data API.

This module provides functions for loading and transforming vocabulary data
from YAML files.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

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


def load_vocabulary_items(
    datafile: str, api_base_url: str
) -> list[dict[str, Any]]:
    """
    Load vocabulary items from a YAML data file.

    This function is called once at app initialization to load
    the vocabulary items into memory for efficient serving.

    Args:
        datafile: Path to the vocabulary data file (YAML format).
        api_base_url: Base URL for the API (used for generating href fields).

    Returns:
        List of vocabulary items with @type field removed and href field added.

    Raises:
        FileNotFoundError: If the data file cannot be found.
        yaml.YAMLError: If the YAML file is malformed.
        ValueError: If the data structure is invalid.
    """
    datafile_path = Path(datafile)

    if not datafile_path.is_file():
        if datafile_path.is_absolute():
            raise FileNotFoundError(f"Data file not found: {datafile_path}")
        # Try resolving relative path
        datafile_path = datafile_path.resolve()
        if not datafile_path.is_file():
            raise FileNotFoundError(f"Data file not found: {datafile_path}")

    log.info(f"Loading vocabulary dataset from: {datafile_path}")

    with open(datafile_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid data format in {datafile_path}")

    # Extract items from @graph and apply transformations
    items = [_transform_item(item) for item in data.get("@graph", [])]

    # Replace placeholder in href fields with actual API base URL
    items_json = str(items)
    items_json = items_json.replace("{API_BASE_URL}", api_base_url)
    import ast

    items = ast.literal_eval(items_json)

    log.info(f"Loaded {len(items)} vocabulary items")

    return items
