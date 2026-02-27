"""
Commands for creating and validating CSV artifacts.

- Create: CSV file from framed JSON-LD using Data Package metadata
- Validate: CSV roundtrip validation (CSV -> JSON-LD -> RDF -> subset check)
"""

import logging
from pathlib import Path
from typing import cast

import click
import yaml

from tools.base import JsonLDFrame
from tools.tabular.validate import TabularValidator
from tools.utils import IGraph

log = logging.getLogger(__name__)


@click.group(name="csv")
def csv():
    """Commands for CSV artifacts."""
    pass


@csv.command(name="create")
@click.option(
    "--jsonld",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the JSON-LD framed file",
)
@click.option(
    "--datapackage",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the datapackage metadata file",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    required=False,
    help="Output path for CSV file. If not specified, uses the path from datapackage metadata. If specified and differs from datapackage path, a warning is shown.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Overwrite output file if it already exists. Without this flag, the command fails if the output file exists.",
)
def create_command(jsonld: Path, datapackage: Path, output: Path, force: bool):
    """Create CSV file from framed JSON-LD using datapackage metadata.

    Output file handling:
    - If --output is not specified, uses the path from datapackage metadata (relative to datapackage directory)
    - If --output differs from datapackage path, a warning is shown
    - If output file exists and --force/-f is not set, the command fails
    - If output file exists and --force/-f is set, the file is overwritten
    """
    click.echo(f"Creating CSV from {jsonld}")

    # Load datapackage to get the expected output path
    datapackage_dict = yaml.safe_load(datapackage.read_text())
    resource = datapackage_dict.get("resources", [{}])[0]
    datapackage_path = resource.get("path", "output.csv")
    expected_output = datapackage.parent / datapackage_path

    # Determine actual output path
    if output is None:
        output = expected_output
        log.debug(f"Using output path from datapackage: {output}")
    else:
        # Check if output differs from datapackage path
        if output.resolve() != expected_output.resolve():
            click.echo(
                f"⚠ Warning: Output path {output} differs from datapackage path {expected_output}",
                err=True,
            )

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
            log.warning(f"Overwriting existing file: {output}")

    create_csv_from_jsonld(jsonld, datapackage, output)
    click.echo(f"✓ Created: {output}")


@csv.command(name="validate")
@click.option(
    "--ttl",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the original RDF vocabulary file in Turtle format",
)
@click.option(
    "--datapackage",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
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
        stats = validate_csv_to_rdf_roundtrip(ttl, datapackage, vocabulary_uri)
        click.secho(
            f"✓ CSV roundtrip validation passed with {stats['csv_rows']} rows"
            f" and {stats['csv_triples']} triples",
            fg="green",
        )
    except Exception as e:
        click.secho(
            f"✗ CSV roundtrip validation failed: {e}", fg="red", err=True
        )
        raise click.Abort() from e


def create_csv_from_jsonld(
    jsonld: Path, datapackage: Path, output: Path
) -> None:
    """Create CSV file from framed JSON-LD using datapackage metadata."""
    from tools.tabular import Tabular

    log.debug(f"Loading JSON-LD data from {jsonld}")
    with jsonld.open(encoding="utf-8") as f:
        jsonld_data = yaml.safe_load(f)
    log.debug(
        f"Loaded JSON-LD data with {len(jsonld_data.get('@graph', []))} items"
    )

    log.debug(f"Loading datapackage metadata from {datapackage}")
    datapackage_dict = yaml.safe_load(datapackage.read_text())

    # Extract the frame (context) from the datapackage
    resource = datapackage_dict.get("resources", [{}])[0]
    context = resource.get("schema", {}).get("x-jsonld-context", {})
    frame = {"@context": context}
    log.debug("Extracted frame context from datapackage")

    # Extract the CSV dialect from the datapackage
    dialect = resource.get("dialect", {})
    log.debug(f"Extracted CSV dialect: {dialect}")

    log.debug("Creating Tabular instance")
    # Create Tabular instance using an "empty" RDF graph
    #   since we will load() pre-framed data.
    tabular = Tabular(
        rdf_data="@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        frame=cast(JsonLDFrame, frame),
        format="turtle",
    )

    log.debug("Loading framed JSON-LD data")
    tabular.load(data=jsonld_data)

    if dialect:
        log.debug("Setting CSV dialect from datapackage")
        tabular.set_dialect(**dialect)

    log.debug("Setting datapackage metadata")
    tabular.datapackage = datapackage_dict

    # Ensure DataFrame has all columns expected by schema
    # Some columns might be aliased in YAML (e.g., label and label_it)
    schema_fields = [
        field["name"] for field in resource.get("schema", {}).get("fields", [])
    ]
    log.debug(f"Schema expects fields: {schema_fields}")
    assert tabular.df is not None, "DataFrame should be loaded at this point"
    log.debug(f"DataFrame has columns: {list(tabular.df.columns)}")

    # Check for missing columns and try to infer them from context
    for field_name in schema_fields:
        if field_name not in tabular.df.columns:
            # Check if this field is an alias for another field
            # by comparing their context definitions
            field_context = context.get(field_name, {})
            if isinstance(field_context, dict):
                # Find if another column has the same @id and @language
                for col in tabular.df.columns:
                    col_context = context.get(col, {})
                    if isinstance(col_context, dict):
                        if col_context.get("@id") == field_context.get(
                            "@id"
                        ) and col_context.get("@language") == field_context.get(
                            "@language"
                        ):
                            log.debug(
                                f"Adding missing column '{field_name}' as copy of '{col}'"
                            )
                            tabular.df[field_name] = tabular.df[col]
                            break

    log.debug(f"Writing CSV to {output}")
    # Write the CSV file
    tabular.to_csv(str(output))
    log.info(f"CSV file created successfully at {output}")


def validate_csv_to_rdf_roundtrip(
    ttl: Path, datapackage: Path, vocabulary_uri: str
) -> dict:
    """
    Validate CSV can roundtrip to RDF and result is subset of original.

    Args:
        ttl: Path to original RDF vocabulary in Turtle format
        datapackage: Path to datapackage metadata with CSV and context
        vocabulary_uri: URI of the vocabulary to validate

    Returns:
        dict: Validation statistics including triple counts
    Raises:
        ValueError: If roundtrip fails or result is not a subset
    """
    log.info(f"Validating CSV roundtrip for {datapackage} against {ttl}")
    tabular_validator: TabularValidator = TabularValidator(
        yaml.safe_load(datapackage.read_text()),
        basepath=datapackage.parent,
    )
    tabular_validator.load()
    log.info("CSV data loaded and validated successfully")
    with ttl.open() as f:
        original_graph = IGraph.parse(source=f, format="turtle")
    log.info(f"Original RDF graph loaded with {len(original_graph)} triples")
    return tabular_validator.validate(
        original_graph=original_graph,
    )
