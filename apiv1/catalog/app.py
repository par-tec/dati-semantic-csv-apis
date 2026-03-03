"""
Vocabularies API application using Connexion.

This module provides a spec-first API for serving controlled vocabularies
in RFC 9727 linkset format.
"""

import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from connexion import AsyncApp, ConnexionMiddleware

from .download import load_linkset_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    TODO: pass datafile path via a config variable in the app.
    """
    logger.info("Application startup: loading vocabularies dataset")
    linkset_data = load_linkset_data()
    logger.info("Application startup complete")

    # Yield state that will be available on request.state
    yield {"linkset_data": linkset_data}

    logger.info("Application shutdown")


def create_app(config: dict | None = None) -> AsyncApp:
    """
    Create and configure the Connexion application.

    This function sets up the API application, including loading the OpenAPI
    specification and configuring the lifespan handler.

    Returns:
        The configured AsyncApp instance.

    TODO: set a config variable with the datafile path.
    """
    config = config or {}
    assert config is not None, "Config must be provided to create_app"
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
