"""
Vocabulary Data API application using Connexion.

This module provides a spec-first API for serving controlled vocabulary data items.
"""

import contextlib
import logging
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import yaml
from connexion import AsyncApp, ConnexionMiddleware
from connexion.exceptions import ProblemException
from connexion.middleware.main import MiddlewarePosition

from .download import load_vocabulary_items
from .errors import (
    handle_exception,
    handle_not_implemented,
    handle_problem_safe,
)
from .printable_parameters_middleware import PrintableParametersMiddleware


class Config(TypedDict):
    API_BASE_URL: str | None
    VOCABULARY_DATAFILE: str
    HARVEST_DB: NotRequired[str | None]


# Configure logging
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def load_dataset_handler(
    datafile: str,
    api_base_url: str,
    harvest_db: str | None,
    app: ConnexionMiddleware,
) -> AsyncIterator[dict[str, Any]]:
    """
    Load the vocabulary dataset at startup
    and makes it available via request.state in all handlers.

    Args:
        datafile: Path to the vocabulary data file.
        api_base_url: Base URL for the API.
        harvest_db: Path to the harvest.db SQLite file, or None.
        app: The ConnexionMiddleware application instance.

    Yields:
        Dictionary containing the application state (vocabulary_items).
    """
    logger.info("Application startup: loading vocabulary dataset")
    vocabulary_items = load_vocabulary_items(
        datafile=datafile, api_base_url=api_base_url
    )

    # Load base OAS spec once for use in show_vocabulary_spec
    with open(Path(__file__).parent / "openapi.yaml") as f:
        base_spec = yaml.safe_load(f)

    # Open a single read-only connection that is reused across all requests
    db_conn: sqlite3.Connection | None = None
    if harvest_db:
        db_conn = sqlite3.connect(harvest_db, check_same_thread=False)
        db_conn.row_factory = sqlite3.Row
        logger.info("Opened harvest DB connection: %s", harvest_db)

    logger.info("Application startup complete")

    yield {
        "vocabulary_items": vocabulary_items,
        "db_connection": db_conn,
        "base_spec": base_spec,
        "api_base_url": api_base_url,
    }

    logger.info("Application shutdown")
    if db_conn:
        db_conn.close()


def create_app(config: Config | None = None) -> AsyncApp:
    """
    Create and configure the Connexion application.

        harvest_db = config.get("HARVEST_DB")
    This function sets up the API application, including loading the OpenAPI
    specification and configuring the lifespan handler.

    Args:
        config: Configuration dictionary with API_BASE_URL and VOCABULARY_DATAFILE.
                vocabulary_datafile, api_base_url, harvest_db, app
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
            vocabulary_datafile,
            api_base_url,
            harvest_db=config.get("HARVEST_DB"),
            app=app,
        ),
    )
    app.add_api(
        "openapi.yaml",
        strict_validation=True,
    )
    app.add_middleware(
        PrintableParametersMiddleware,
        position=MiddlewarePosition.BEFORE_CONTEXT,
    )

    # Register exception handler for generic exceptions
    app.add_error_handler(NotImplementedError, handle_not_implemented)
    app.add_error_handler(501, handle_not_implemented)
    app.add_error_handler(500, handle_exception)
    app.add_error_handler(Exception, handle_exception)
    app.add_error_handler(ProblemException, handle_problem_safe)

    return app
