"""
CLI commands for vocabulary artifact management.

Organized by artifact type:
- jsonld: JSON-LD framed representations from RDF
- datapackage: Frictionless Data Package metadata
- csv: CSV serialization
- openapi: OpenAPI specifications
"""

import logging
from importlib.metadata import PackageNotFoundError, version

import click

from tools._build_info import BUILD_COMMIT
from tools.commands.csv import csv
from tools.commands.datapackage import datapackage
from tools.commands.jsonld import jsonld
from tools.commands.openapi import openapi

log = logging.getLogger(__name__)


def _cli_version_string() -> str:
    """Return CLI version string including build commit if available."""
    try:
        pkg_version = version("dati-semantic-apis")
    except PackageNotFoundError:
        pkg_version = "0+unknown"

    if BUILD_COMMIT and BUILD_COMMIT != "unknown":
        return f"{pkg_version}+{BUILD_COMMIT}"

    return pkg_version


LOG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


def common_options(func):
    func = click.option(
        "--log-level",
        "-l",
        type=click.Choice(LOG_LEVELS, case_sensitive=False),
        default="INFO",
        help="Set the logging level.",
    )(func)
    return func


@click.group(epilog=f"Version: {_cli_version_string()}")
@click.version_option(version=_cli_version_string())
@common_options
def cli(log_level):
    """CLI for creating and validating vocabulary artifacts."""
    logging.basicConfig(level=getattr(logging, log_level))


cli.add_command(jsonld)
cli.add_command(datapackage)
cli.add_command(csv)
cli.add_command(openapi)

__all__ = ["cli"]
