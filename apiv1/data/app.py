"""
Vocabulary Data API application using Connexion.

This module provides a spec-first API for serving controlled vocabulary data items.
"""

import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TypedDict

from connexion import AsyncApp, ConnexionMiddleware
from connexion.exceptions import ProblemException

from .download import load_vocabulary_items
from .errors import (
    handle_exception,
    handle_not_implemented,
    handle_problem_safe,
)


class Config(TypedDict):
    API_BASE_URL: str | None
    VOCABULARY_DATAFILE: str


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def load_dataset_handler(
    datafile: str,
    api_base_url: str,
    app: ConnexionMiddleware,
) -> AsyncIterator[dict[str, Any]]:
    """
    Load the vocabulary dataset at startup
    and makes it available via request.state in all handlers.

    Args:
        datafile: Path to the vocabulary data file.
        api_base_url: Base URL for the API.
        app: The ConnexionMiddleware application instance.

    Yields:
        Dictionary containing the application state (vocabulary_items).
    """
    logger.info("Application startup: loading vocabulary dataset")
    vocabulary_items = load_vocabulary_items(
        datafile=datafile, api_base_url=api_base_url
    )
    logger.info("Application startup complete")

    # Yield state that will be available on request.state
    yield {"vocabulary_items": vocabulary_items}

    logger.info("Application shutdown")


def create_app(config: Config | None = None) -> AsyncApp:
    """
    Create and configure the Connexion application.

    This function sets up the API application, including loading the OpenAPI
    specification and configuring the lifespan handler.

    Args:
        config: Configuration dictionary with API_BASE_URL and VOCABULARY_DATAFILE.

    Returns:
        The configured AsyncApp instance.
    """
    if config is None:
        config = Config(
            API_BASE_URL="http://localhost:8080",
            VOCABULARY_DATAFILE="assets/controlled-vocabularies/agente_causale/latest/agente_causale.data.yaml",
        )
    assert config is not None, "Config must be provided to create_app"

    api_base_url = config.get("API_BASE_URL") or "http://localhost:8080"
    vocabulary_datafile = config["VOCABULARY_DATAFILE"]

    app: AsyncApp = AsyncApp(
        import_name=__name__,
        specification_dir=str(Path(__file__).parent),
        lifespan=lambda app: load_dataset_handler(
            vocabulary_datafile, api_base_url, app
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
    app.add_error_handler(ProblemException, handle_problem_safe)

    return app
