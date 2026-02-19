"""
A CLI wrapping multiple commands to validate vocabulary artifacts:

1. JSON-LD validation: Validates that a framed JSON-LD representation is a subset
   of the original RDF vocabulary (graph isomorphism check)

2. Datapackage validation: Validates a Frictionless Data Package metadata file:
   - Validates against datapackage schema
   - Checks CSV file path exists
   - Validates CSV dialect configuration
   - Validates CSV content against schema
   - Verifies x-jsonld-context property for CSV to RDF mapping
   - Optionally validates x-jsonld-type for RDF class associations

3. CSV roundtrip validation: Validates that CSV data can be:
   - Re-framed into JSON-LD using x-jsonld-context
   - Converted back to RDF
   - Result MUST be a subset of the original RDF vocabulary


"""

from pathlib import Path

import click


@click.group()
def cli():
    """CLI for validating vocabulary artifacts."""
    pass


@cli.command(name="jsonld")
@click.option(
    "--ttl",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the original RDF vocabulary file in Turtle format",
)
@click.option(
    "--jsonld",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the JSON-LD framed file to validate",
)
@click.option(
    "--vocabulary-uri",
    type=str,
    required=True,
    help="URI of the vocabulary (ConceptScheme) to validate",
)
def validate_jsonld_command(ttl: Path, jsonld: Path, vocabulary_uri: str):
    """
    Validate that JSON-LD framed representation is a subset of original RDF.

    Performs graph isomorphism check to ensure the framed JSON-LD contains
    only data present in the original RDF vocabulary.
    """
    click.echo(f"Validating JSON-LD {jsonld} against {ttl}")
    click.echo(f"Vocabulary URI: {vocabulary_uri}")

    try:
        validate_jsonld_subset(ttl, jsonld, vocabulary_uri)
        click.secho("✓ JSON-LD validation passed", fg="green")
    except Exception as e:
        click.secho(f"✗ JSON-LD validation failed: {e}", fg="red", err=True)
        raise click.Abort() from e


@cli.command(name="datapackage")
@click.option(
    "--datapackage",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the datapackage metadata file (YAML/JSON)",
)
@click.option(
    "--check-csv/--no-check-csv",
    default=True,
    help="Validate CSV file content (default: yes)",
)
def validate_datapackage_command(datapackage: Path, check_csv: bool):
    """
    Validate Frictionless Data Package metadata and CSV content.

    Validates:
    - Datapackage schema compliance
    - CSV file existence and accessibility
    - CSV dialect configuration
    - CSV content against schema
    - x-jsonld-context presence and structure
    """
    click.echo(f"Validating datapackage: {datapackage}")

    try:
        validate_datapackage_metadata(datapackage, check_csv)
        click.secho("✓ Datapackage validation passed", fg="green")
    except Exception as e:
        click.secho(f"✗ Datapackage validation failed: {e}", fg="red", err=True)
        raise click.Abort() from e


@cli.command(name="csv-roundtrip")
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
def validate_csv_roundtrip_command(ttl: Path, datapackage: Path, vocabulary_uri: str):
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
        click.secho(f"✗ CSV roundtrip validation failed: {e}", fg="red", err=True)
        raise click.Abort() from e


def validate_jsonld_subset(ttl: Path, jsonld: Path, vocabulary_uri: str) -> None:
    """
    Validate that JSON-LD framed representation is a subset of original RDF.

    Args:
        ttl: Path to original RDF vocabulary in Turtle format
        jsonld: Path to JSON-LD framed file
        vocabulary_uri: URI of the vocabulary to validate

    Raises:
        ValueError: If JSON-LD contains data not in original RDF
    """
    raise NotImplementedError("validate_jsonld_subset not yet implemented")


def validate_datapackage_metadata(datapackage: Path, check_csv: bool) -> None:
    """
    Validate Frictionless Data Package metadata and optionally CSV content.

    Args:
        datapackage: Path to datapackage metadata file
        check_csv: Whether to validate CSV file content

    Raises:
        ValueError: If datapackage is invalid or CSV validation fails
    """
    raise NotImplementedError("validate_datapackage_metadata not yet implemented")


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
    raise NotImplementedError("validate_csv_to_rdf_roundtrip not yet implemented")


if __name__ == "__main__":
    cli()
