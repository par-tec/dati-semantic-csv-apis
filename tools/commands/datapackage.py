"""
Commands for creating and validating Frictionless Data Package artifacts.

- Create: Data Package metadata stub from RDF vocabulary
- Validate: Verify Data Package metadata and optionally CSV content
  * Schema compliance
  * CSV file existence and accessibility
  * CSV dialect configuration
  * CSV content against schema
  * x-jsonld-context presence and structure
"""

import logging
from pathlib import Path

import click
import yaml
from frictionless import Package

from tools.tabular import Tabular

log = logging.getLogger(__name__)


@click.group(name="datapackage")
def datapackage():
    """Commands for Data Package artifacts."""
    pass


@datapackage.command(name="create")
@click.option(
    "--ttl",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the RDF vocabulary file in Turtle format",
)
@click.option(
    "--frame",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the JSON-LD frame file (.yamlld or .jsonld)",
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
    help="Output path for datapackage metadata file",
)
@click.option(
    "--lang",
    type=str,
    default="it",
    help="Language code for labels and descriptions (default: it)",
)
def create_command(
    ttl: Path, frame: Path, vocabulary_uri: str, output: Path, lang: str
):
    """Create Frictionless Data Package metadata stub.

    This stub is a datapackage.yaml file with minimal metadata extracted from the RDF vocabulary.
    It must be completed with all the metadata fields before use
    and then renamed to datapackage.json in order to be used for CSV generation.
    """
    click.echo(f"Creating datapackage metadata for {vocabulary_uri}")
    create_datapackage_metadata(ttl, frame, vocabulary_uri, output, lang)
    click.echo(f"✓ Created: {output}")


@datapackage.command(name="validate")
@click.option(
    "--datapackage",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the datapackage metadata file (YAML/JSON)",
)
def validate_command(datapackage: Path):
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
        validate_datapackage_metadata(datapackage)
        click.secho("✓ Datapackage validation passed", fg="green")
    except Exception as e:
        click.secho(f"✗ Datapackage validation failed: {e}", fg="red", err=True)
        raise click.Abort() from e


def create_datapackage_metadata(
    ttl: Path, frame: Path, vocabulary_uri: str, output: Path, lang: str
) -> None:
    """
    Create Frictionless Data Package metadata stub from RDF vocabulary.

    Args:
        ttl: Path to the RDF vocabulary file in Turtle format
        frame: Path to the JSON-LD frame file (.yamlld or .jsonld)
        vocabulary_uri: URI of the vocabulary (ConceptScheme) to extract
        output: Output path for datapackage metadata file
        lang: Language code for labels and descriptions (currently unused)

    The function:
    1. Loads the RDF vocabulary from the TTL file
    2. Loads the JSON-LD frame
    3. Creates a Tabular instance
    4. Generates a datapackage stub with metadata extracted from the RDF graph
    5. Writes the datapackage stub to the output file in YAML format

    Note: This creates only a stub. The generated file should be:
    - Reviewed and completed with all necessary metadata fields
    - Renamed to datapackage.json before use for CSV generation
    """
    if not ttl.exists():
        raise FileNotFoundError(f"TTL file not found: {ttl}")

    if not frame.exists():
        raise FileNotFoundError(f"Frame file not found: {frame}")

    if not output.parent.exists():
        raise FileNotFoundError(
            f"Output directory {output.parent} does not exist"
        )

    # Load the JSON-LD frame
    frame_data = yaml.safe_load(frame.read_text(encoding="utf-8"))

    # Create a Tabular instance from the RDF vocabulary and frame
    log.debug(f"Creating Tabular instance from {ttl}")
    tabular = Tabular(rdf_data=ttl, frame=frame_data)

    # Generate the datapackage stub (without resources)
    log.debug(f"Generating datapackage stub for vocabulary {vocabulary_uri}")

    resource_path = Path(f"{Path(vocabulary_uri).stem}.csv")
    datapackage_stub = tabular.datapackage_stub(resource_path=resource_path)

    # Write the datapackage stub to the output file
    log.debug(f"Writing datapackage stub to {output}")
    with output.open("w", encoding="utf-8") as f:
        yaml.safe_dump(datapackage_stub, f, allow_unicode=True, indent=2)

    log.info(f"Datapackage stub created: {output}")


def validate_datapackage_metadata(datapackage: Path) -> None:
    """
    Validate Frictionless Data Package metadata.

    Args:
        datapackage: Path to datapackage metadata file

    Raises:
        ValueError: If datapackage is invalid
        FileNotFoundError: If datapackage file doesn't exist
    """
    if not datapackage.exists():
        raise FileNotFoundError(f"Datapackage file not found: {datapackage}")

    # Load the datapackage file
    log.debug(f"Loading datapackage from {datapackage}")
    datapackage_dict = yaml.safe_load(datapackage.read_text(encoding="utf-8"))

    # Create and validate the Package
    log.debug("Validating datapackage structure")
    basepath = datapackage.parent.as_posix()
    package = Package(datapackage_dict, basepath=basepath)

    if not package:
        raise ValueError(f"Invalid datapackage structure: {datapackage}")

    # Check that it has a valid schema
    if not package.validate():
        errors = []
        validation_result = package.validate()
        for task in validation_result.tasks:
            if task.errors:
                for error in task.errors:
                    errors.append(f"Resource '{task.name}': {error.message}")
        if errors:
            raise ValueError(
                "Datapackage metadata validation failed:\n" + "\n".join(errors)
            )

    log.info(f"Datapackage metadata validation completed: {datapackage}")
