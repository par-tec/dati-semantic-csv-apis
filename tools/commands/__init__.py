"""
CLI commands for vocabulary artifact management.

Organized by artifact type:
- jsonld: JSON-LD framed representations from RDF
- datapackage: Frictionless Data Package metadata
- csv: CSV serialization
- openapi: OpenAPI specifications
"""

import logging

import click

from tools.commands.csv import csv
from tools.commands.datapackage import datapackage
from tools.commands.jsonld import jsonld
from tools.commands.openapi import openapi

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@click.group()
def cli():
    """CLI for creating and validating vocabulary artifacts."""
    pass


cli.add_command(jsonld)
cli.add_command(datapackage)
cli.add_command(csv)
cli.add_command(openapi)

__all__ = ["cli"]
