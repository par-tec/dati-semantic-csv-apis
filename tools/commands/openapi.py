"""
Commands for creating OpenAPI artifacts.

- Create: OpenAPI specification from framed JSON-LD and frame
"""

import logging
from pathlib import Path

import click
import yaml

from tools.base import JsonLDFrame
from tools.openapi.openapi_generator import Apiable

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
    required=False,
    help="Path to the JSON-LD framed file",
)
@click.option(
    "--ttl",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=False,
    help="Path to the RDF vocabulary file in Turtle format",
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
    "--vocabulary-uri",
    type=str,
    required=True,
    help="URI of the vocabulary (ConceptScheme) to extract",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    required=True,
    help="Output path for OpenAPI specification",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Overwrite output file if it already exists. Without this flag, the command fails if the output file exists.",
)
def create_command(
    jsonld: Path | None,
    ttl: Path | None,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
    force: bool,
):
    """Create OpenAPI specification from framed JSON-LD or RDF vocabulary."""
    if jsonld is None and ttl is None:
        raise click.UsageError("Please provide one of --jsonld or --ttl.")

    if jsonld is not None and ttl is not None:
        raise click.UsageError(
            "Please provide only one of --jsonld or --ttl, not both."
        )

    click.echo(f"Creating openapi metadata for {vocabulary_uri}")

    # Check if output file exists
    if output.exists():
        if not force:
            click.secho(
                f"✗ Error: Output file {output} already exists. Use --force/-f to overwrite.",
                fg="red",
                err=True,
            )
            raise click.Abort()
        else:
            log.debug(f"Overwriting existing file: {output}")

    create_oas_spec(jsonld, ttl, frame, vocabulary_uri, output)
    click.echo(f"✓ Created: {output}")


def create_oas_spec(
    jsonld: Path | None,
    ttl: Path | None,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
) -> None:
    """Create OpenAPI specification from framed JSON-LD or RDF vocabulary.

    Args:
        jsonld: Path to JSON-LD framed file (optional)
        ttl: Path to RDF Turtle file (optional)
        frame: Path to JSON-LD frame file
        vocabulary_uri: URI of the vocabulary
        output: Output path for OpenAPI specification

    Raises:
        ValueError: If neither jsonld nor ttl is provided
    """
    # Load the frame
    frame_data = JsonLDFrame.load(frame)

    # Create Apiable instance from either TTL or JSONLD
    if ttl is not None:
        log.debug(f"Creating OpenAPI spec from TTL file: {ttl}")
        apiable = Apiable(rdf_data=ttl, frame=frame_data, format="text/turtle")
    elif jsonld is not None:
        log.debug(f"Creating OpenAPI spec from JSON-LD file: {jsonld}")
        jsonld_data = yaml.safe_load(jsonld.read_text(encoding="utf-8"))
        apiable = Apiable(rdf_data=jsonld_data, frame=frame_data)
    else:
        raise ValueError("Either jsonld or ttl must be provided")

    # Generate OpenAPI specification
    log.debug("Generating OpenAPI specification")
    openapi_spec = apiable.openapi(
        add_constraints=True,
        validate_output=True,
    )

    # Write to output file
    log.debug(f"Writing OpenAPI specification to {output}")
    with output.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            openapi_spec, f, allow_unicode=True, indent=2, sort_keys=True
        )

    log.info(f"openapi stub created: {output}")


@openapi.command(name="validate")
@click.option(
    "--openapi",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the OpenAPI specification file to validate",
)
def validate_command(openapi: Path):
    """
    Validate OpenAPI specification file.

    Validates that the file:
    - Is valid YAML/JSON
    - Conforms to OpenAPI 3.0 schema
    """
    click.echo(f"Validating openapi: {openapi}")

    try:
        validate_openapi_spec(openapi)
        click.secho("✓ openapi validation passed", fg="green")
    except Exception as e:
        click.secho(f"✗ openapi validation failed: {e}", fg="red", err=True)
        raise click.Abort() from e


def validate_openapi_spec(openapi_path: Path) -> None:
    """
    Validate OpenAPI specification file.

    Args:
        openapi_path: Path to OpenAPI specification file

    Raises:
        ValueError: If OpenAPI spec is invalid
        FileNotFoundError: If file doesn't exist
    """
    from jsonschema import ValidationError, validate

    from tools.openapi.openapi_generator import OAS30_SCHEMA

    if not openapi_path.exists():
        raise FileNotFoundError(f"OpenAPI file not found: {openapi_path}")

    # Load the OpenAPI file
    log.debug(f"Loading OpenAPI spec from {openapi_path}")
    openapi_dict = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))

    # Validate against OAS 3.0 schema
    log.debug("Validating OpenAPI spec against OAS 3.0 schema")
    try:
        validate(instance=openapi_dict, schema=OAS30_SCHEMA)
    except ValidationError as e:
        raise ValueError(
            f"OpenAPI validation failed: {e.message} at path {list(e.path)}"
        ) from e

    log.info(f"OpenAPI validation completed: {openapi_path}")
