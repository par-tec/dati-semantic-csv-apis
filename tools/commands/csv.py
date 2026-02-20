"""
Commands for creating and validating CSV artifacts.

- Create: CSV file from framed JSON-LD using Data Package metadata
- Validate: CSV roundtrip validation (CSV -> JSON-LD -> RDF -> subset check)
"""

import logging
from pathlib import Path

import click

log = logging.getLogger(__name__)


@click.group(name="csv")
def csv():
    """Commands for CSV artifacts."""
    pass


@csv.command(name="create")
@click.option(
    "--jsonld",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the JSON-LD framed file",
)
@click.option(
    "--datapackage",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the datapackage metadata file",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=False,
    help="Output path for CSV file. By default this is defined in the datapackage metadata.",
)
def create_command(jsonld: Path, datapackage: Path, output: Path):
    """Create CSV file from framed JSON-LD using datapackage metadata."""
    click.echo(f"Creating CSV from {jsonld}")
    create_csv_from_jsonld(jsonld, datapackage, output)
    click.echo(f"✓ Created: {output}")


@csv.command(name="validate")
@click.option(
    "--ttl",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the original RDF vocabulary file in Turtle format",
)
@click.option(
    "--datapackage",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the datapackage metadata file containing CSV and context",
)
@click.option(
    "--vocabulary-uri",
    type=str,
    required=True,
    help="URI of the vocabulary (ConceptScheme) to validate",
)
def validate_command(ttl: Path, datapackage: Path, vocabulary_uri: str):
    """
    Validate CSV roundtrip: CSV → JSON-LD → RDF → subset check.

    Validates that:
    1. CSV can be read using datapackage metadata
    2. CSV data can be re-framed to JSON-LD using x-jsonld-context
    3. JSON-LD can be converted to RDF
    4. Resulting RDF is a subset of original vocabulary
    """
    click.echo(f"Validating CSV roundtrip for {datapackage}")
    click.echo(f"Original vocabulary: {ttl}")
    click.echo(f"Vocabulary URI: {vocabulary_uri}")

    try:
        validate_csv_to_rdf_roundtrip(ttl, datapackage, vocabulary_uri)
        click.secho("✓ CSV roundtrip validation passed", fg="green")
    except Exception as e:
        click.secho(
            f"✗ CSV roundtrip validation failed: {e}", fg="red", err=True
        )
        raise click.Abort() from e


def create_csv_from_jsonld(
    jsonld: Path, datapackage: Path, output: Path
) -> None:
    """Create CSV file from framed JSON-LD using datapackage metadata."""
    raise NotImplementedError("create_csv_from_jsonld not yet implemented")


def validate_csv_to_rdf_roundtrip(
    ttl: Path, datapackage: Path, vocabulary_uri: str
) -> None:
    """
    Validate CSV can roundtrip to RDF and result is subset of original.

    Args:
        ttl: Path to original RDF vocabulary in Turtle format
        datapackage: Path to datapackage metadata with CSV and context
        vocabulary_uri: URI of the vocabulary to validate

    Raises:
        ValueError: If roundtrip fails or result is not a subset
    """
    raise NotImplementedError(
        "validate_csv_to_rdf_roundtrip not yet implemented"
    )
