"""
Vocabulary Data API application using Connexion.

This module provides a spec-first API for serving controlled vocabulary data items.
"""

import contextlib
import logging
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TypedDict

import yaml
from common.errors import (
    handle_exception,
    handle_not_implemented,
    handle_problem_safe,
)
from common.printable_parameters_middleware import (
    PrintableParametersMiddleware,
)
from connexion import AsyncApp, ConnexionMiddleware
from connexion.exceptions import ProblemException
from connexion.middleware.main import MiddlewarePosition

from tools.store import APIStore


class Config(TypedDict):
    API_BASE_URL: str
    HARVEST_DB: str


# Configure logging
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _validate_db(harvest_db: str) -> None:
    """Validate that the datastore file exists and has the expected structure."""
    try:
        with APIStore(harvest_db, read_only=True) as db:
            db.validate_metadata_schema()
            db.validate_metadata_content()
    except Exception as e:
        logger.error(
            "Error validating datastore %s: %s", Path(harvest_db).absolute(), e
        )
        raise ValueError(
            f"Invalid datastore {Path(harvest_db).absolute()}: {e}"
        ) from e


@contextlib.asynccontextmanager
async def load_dataset_handler(
    api_base_url: str,
    harvest_db: str,
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
    vocabulary_items = None
    assert harvest_db

    # Load base OAS spec once for use in show_vocabulary_spec
    with open(Path(__file__).parent / "openapi.yaml") as f:
        base_spec = yaml.safe_load(f)

    _validate_db(harvest_db)

    # Open a single read-only APIStore instance reused across requests.
    harvest_database: APIStore = APIStore(
        harvest_db,
        read_only=True,
        check_same_thread=False,
    )
    harvest_database.connect()
    logger.info("Opened harvest DB connection: %s", harvest_db)

    logger.info("Application startup complete")

    yield {
        "vocabulary_items": vocabulary_items,
        "harvest_db": harvest_database,
        "base_spec": base_spec,
        "api_base_url": api_base_url,
    }

    logger.info("Application shutdown")
    if harvest_database:
        harvest_database.close()


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
            HARVEST_DB="harvest.db",
        )
    assert config is not None, "Config must be provided to create_app"

    api_base_url = config.get("API_BASE_URL") or "http://localhost:8080"

    app: AsyncApp = AsyncApp(
        import_name=__name__,
        specification_dir=str(Path(__file__).parent),
        lifespan=lambda app: load_dataset_handler(
            api_base_url,
            harvest_db=config.get("HARVEST_DB"),
            app=app,
        ),
    )
    app.add_api(
        "openapi.yaml",
        strict_validation=True,
    )
    # Ensure that request parameters are safe (e.g., for logging, ..)
    app.add_middleware(
        PrintableParametersMiddleware,
        position=MiddlewarePosition.BEFORE_CONTEXT,
    )

    # Register exception handler for generic exceptions
    app.add_error_handler(NotImplementedError, handle_not_implemented)
    app.add_error_handler(501, handle_not_implemented)
    app.add_error_handler(500, handle_exception)
    app.add_error_handler(Exception, handle_exception)

    # Specific sql Handlers.
    app.add_error_handler(sqlite3.OperationalError, handle_exception)
    app.add_error_handler(sqlite3.DatabaseError, handle_exception)

    app.add_error_handler(ProblemException, handle_problem_safe)

    #
    # We use assertion errors to track unexpected conditions
    #   that are elsewhere tested. These should be
    #   logged and fixed in the code.
    #
    app.add_error_handler(AssertionError, handle_exception)

    return app
