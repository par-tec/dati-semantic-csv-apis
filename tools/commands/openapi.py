"""
Commands for creating OpenAPI artifacts.

- Create: OpenAPI specification from framed JSON-LD and frame
"""

import logging
from pathlib import Path

import click
import yaml

from tools.base import TEXT_TURTLE, JsonLDFrame
from tools.commands.utils import check_output_file
from tools.openapi import Apiable

log = logging.getLogger(__name__)


@click.group(name="openapi")
def openapi():
    """Commands for OpenAPI artifacts."""
    pass


@openapi.command(name="create")
@click.option(
    "--ttl",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the RDF vocabulary file in Turtle format",
)
@click.option(
    "--jsonld",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the pre-framed JSON-LD data file",
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
@click.option(
    "--max-samples",
    type=int,
    default=0,
    show_default=True,
    help="Maximum number of records to use for schema inference. 0 means use all records (no sampling).",
)
def create_command(
    ttl: Path,
    jsonld: Path,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
    force: bool,
    max_samples: int,
):
    """Create OpenAPI specification from pre-framed JSON-LD and RDF vocabulary metadata."""
    click.echo(f"Creating openapi metadata for {vocabulary_uri}")

    check_output_file(output, force)

    create_oas_spec(
        ttl=ttl,
        jsonld=jsonld,
        frame=frame,
        vocabulary_uri=vocabulary_uri,
        output=output,
        max_samples=max_samples or None,
    )
    click.echo(f"✓ Created: {output}")


def create_oas_spec(
    ttl: Path,
    jsonld: Path,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
    max_samples: int | None = None,
) -> Apiable | None:
    """Create OpenAPI specification stub from pre-framed JSON-LD and RDF vocabulary metadata.

    :warning: This stub must be manually edited by the data provider in order to
    validate its content.

    Args:
        ttl: Path to RDF Turtle file (for vocabulary metadata)
        jsonld: Path to pre-framed JSON-LD data file
        frame: Path to JSON-LD frame file
        vocabulary_uri: URI of the vocabulary
        output: Output path for OpenAPI specification
    """
    frame_data = JsonLDFrame.load(frame)

    log.debug(
        f"Loading vocabulary metadata from TTL: {ttl}, data from JSON-LD: {jsonld}"
    )
    apiable = Apiable(rdf_data=ttl, frame=frame_data, format=TEXT_TURTLE)
    with jsonld.open() as f:
        apiable.json_ld = yaml.safe_load(f)

    # Generate OpenAPI specification
    log.debug("Generating OpenAPI specification")
    openapi_spec = apiable.openapi(
        add_constraints=True,
        validate_output=True,
        max_samples=max_samples,
    )

    # Write to output file
    log.debug(f"Writing OpenAPI specification to {output}")
    with output.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            openapi_spec, f, allow_unicode=True, indent=2, sort_keys=True
        )

    log.info(f"openapi stub created: {output}")
    return apiable


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

    from tools.openapi import OAS30_SCHEMA

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
