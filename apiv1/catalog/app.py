"""
Vocabularies API application using Connexion.

This module provides a spec-first API for serving controlled vocabularies
in RFC 9727 linkset format.
"""

import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TypedDict

from connexion import AsyncApp, ConnexionMiddleware

from .download import load_linkset_data
from .errors import handle_exception, handle_not_implemented


class Config(TypedDict):
    SPARQL_URL: str | None
    API_BASE_URL: str | None
    VOCABULARIES_DATAFILE: str


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def load_dataset_handler(
    datafile: str,
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
    linkset_data = load_linkset_data(datafile=datafile)
    logger.info("Application startup complete")

    # Yield state that will be available on request.state
    yield {"linkset_data": linkset_data}

    logger.info("Application shutdown")


def create_app(config: Config | None = None) -> AsyncApp:
    """
    Create and configure the Connexion application.

    This function sets up the API application, including loading the OpenAPI
    specification and configuring the lifespan handler.

    Returns:
        The configured AsyncApp instance.

    TODO: set a config variable with the datafile path.
    """
    if config is None:
        config = Config(
            SPARQL_URL=None,
            API_BASE_URL=None,
            VOCABULARIES_DATAFILE="vocabularies.linkset.yaml",
        )
    assert config is not None, "Config must be provided to create_app"
    app: AsyncApp = AsyncApp(
        import_name=__name__,
        specification_dir=str(Path(__file__).parent),
        lifespan=lambda app: load_dataset_handler(
            config["VOCABULARIES_DATAFILE"], app
        ),
    )
    app.add_api(
        "openapi.yaml",
        strict_validation=True,
    )

    # Register exception handler for generic exceptions
    app.add_error_handler(NotImplementedError, handle_not_implemented)
    app.add_error_handler(501, handle_not_implemented)
    app.add_error_handler(500, handle_exception)
    app.add_error_handler(Exception, handle_exception)

    return app
