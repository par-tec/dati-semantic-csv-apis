"""
Vocabularies API application using Connexion.

This module provides a spec-first API for serving controlled vocabularies
in RFC 9727 linkset format.
"""

import contextlib
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import yaml
from connexion import AsyncApp, ConnexionMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_linkset_data() -> dict[str, Any]:
    """
    Load linkset data from the configured YAML file.

    This function is called once at app initialization to load
    the vocabularies linkset into memory for efficient serving.

    Returns:
        The parsed linkset data structure.

    Raises:
        FileNotFoundError: If the data file cannot be found.
        yaml.YAMLError: If the YAML file is malformed.
    """
    datafile: str = os.getenv(
        "VOCABULARIES_DATAFILE", "vocabularies.linkset.yaml"
    )

    datafile_path = Path(datafile)

    if not datafile_path.is_file():
        if datafile_path.is_absolute():
            raise FileNotFoundError(f"Data file not found: {datafile_path}")
        # Try resolving relative path
        datafile_path = datafile_path.resolve()
        if not datafile_path.is_file():
            raise FileNotFoundError(f"Data file not found: {datafile_path}")

    logger.info(f"Loading vocabularies dataset from: {datafile_path}")

    with open(datafile_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "linkset" not in data:
        raise ValueError(f"Invalid linkset format in {datafile_path}")

    logger.info(
        f"Loaded {len(data.get('linkset', [{}])[0].get('item', []))} vocabulary items"
    )

    return data


@contextlib.asynccontextmanager
async def load_dataset_handler(
    app: ConnexionMiddleware,
) -> AsyncIterator[dict[str, Any]]:
    """
    Load the vocabularies dataset at startup
    and makes it available via request.state in all handlers.

    Args:
        app: The ConnexionMiddleware application instance.

    Yields:
        Dictionary containing the application state (linkset_data).
    """
    logger.info("Application startup: loading vocabularies dataset")
    linkset_data = _load_linkset_data()
    logger.info("Application startup complete")

    # Yield state that will be available on request.state
    yield {"linkset_data": linkset_data}

    logger.info("Application shutdown")


def create_app() -> AsyncApp:
    """
    Create and configure the Connexion application.

    This function sets up the API application, including loading the OpenAPI
    specification and configuring the lifespan handler.

    Returns:
        The configured AsyncApp instance.
    """
    app: AsyncApp = AsyncApp(
        import_name=__name__,
        specification_dir=str(Path(__file__).parent),
        lifespan=load_dataset_handler,
    )

    app.add_api(
        "openapi.yaml",
        strict_validation=True,
    )

    return app
