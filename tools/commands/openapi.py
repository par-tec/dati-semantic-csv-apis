"""
Commands for creating OpenAPI artifacts.

- Create: OpenAPI specification from framed JSON-LD and frame
"""

import logging
from pathlib import Path

import click

log = logging.getLogger(__name__)


@click.group(name="openapi")
def openapi():
    """Commands for OpenAPI artifacts."""
    pass


@openapi.command(name="create")
@click.option(
    "--jsonld",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the JSON-LD framed file",
)
@click.option(
    "--frame",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the JSON-LD frame used to create the jsonld file",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    required=True,
    help="Output path for OpenAPI specification",
)
def create_command(jsonld: Path, frame: Path, output: Path):
    """Create OpenAPI specification from framed JSON-LD."""
    click.echo(f"Creating OpenAPI spec from {jsonld}")
    create_oas_spec(jsonld, frame, output)
    click.echo(f"✓ Created: {output}")


def create_oas_spec(jsonld: Path, frame: Path, output: Path) -> None:
    """Create OpenAPI specification from framed JSON-LD."""
    raise NotImplementedError("create_oas_spec not yet implemented")
