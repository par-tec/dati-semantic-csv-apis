"""
A CLI wrapping multiple commands to create vocabulary artifacts:

- A JSON-LD framed representation of an RDF vocabulary given the TTL file and a JSON-LD frame.
- A stub Frictionless Data Package metadata file generated
  from the RDF vocabulary data and containing:
  * target CSV file path
  * CSV dialect information
  * schema to validate the CSV content
  * the x-jsonld-context property to map CSV fields to RDF properties.
  * optionally, the x-jsonld-type to associate a specific RDF class to each row in the CSV file.

  This stub is a minimal metadata fileor the vocabulary data from the RDF vocabulary and the JSON-LD frame,
  that must be later completed with all the metadata fields.
- An OAS definition for the vocabulary API given the framed JSON-LD data created above.
- A CSV representation of the framed JSON-LD data given the datapackage metadata, using proper CSV dialect and quoting
  specified in the datapackage metadata.
"""

from pathlib import Path

import click
import yaml


@click.group()
def cli():
    """CLI for creating vocabulary artifacts from RDF data."""
    pass


@cli.command(name="framed")
@click.option(
    "--ttl",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the RDF vocabulary file in Turtle format",
)
@click.option(
    "--frame",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
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
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output path for JSON-LD framed file",
)
@click.option(
    "--frame-only",
    is_flag=True,
    help="If set, the framed JSON-LD will only include"
    " fields defined in the frame context,"
    " even if they are present in the original RDF graph.",
    default=False,
)
@click.option(
    "--batch-size",
    type=int,
    default=0,
    help="Number of RDF triples to process in each batch when framing. "
    "Set to 0 to process all triples at once (default: 0).",
)
def frame_command(
    ttl: Path,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
    frame_only: bool,
    batch_size: int,
):
    """Create JSON-LD framed representation from RDF vocabulary."""
    click.echo(f"Framing vocabulary {vocabulary_uri} from {ttl}")
    create_jsonld_framed(
        ttl, frame, vocabulary_uri, output, frame_only, batch_size
    )
    click.echo(f"✓ Created: {output}")


@cli.command(name="datapackage-stub")
@click.option(
    "--ttl",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the RDF vocabulary file in Turtle format",
)
@click.option(
    "--frame",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
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
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output path for datapackage metadata file",
)
@click.option(
    "--lang",
    type=str,
    default="it",
    help="Language code for labels and descriptions (default: it)",
)
def datapackage_command(
    ttl: Path, frame: Path, vocabulary_uri: str, output: Path, lang: str
):
    """Create Frictionless Data Package metadata stub.

    This stub is datapackage.yaml file with minimal metadata extracted from the RDF vocabulary.
    It must be completed with all the metadata fields before use
    and then renamed to datapackage.json in order to be used
    for CSV generation.
    """
    click.echo(f"Creating datapackage metadata for {vocabulary_uri}")
    create_datapackage_metadata(ttl, frame, vocabulary_uri, output, lang)
    click.echo(f"✓ Created: {output}")


@cli.command(name="openapi")
@click.option(
    "--jsonld",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the JSON-LD framed file",
)
@click.option(
    "--frame",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the JSON-LD frame used to create the jsonld file",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output path for OpenAPI specification",
)
def openapi_command(jsonld: Path, frame: Path, output: Path):
    """Create OpenAPI specification from framed JSON-LD."""
    click.echo(f"Creating OpenAPI spec from {jsonld}")
    create_oas_spec(jsonld, frame, output)
    click.echo(f"✓ Created: {output}")


@cli.command(name="csv")
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
def csv_command(jsonld: Path, datapackage: Path, output: Path):
    """Create CSV file from framed JSON-LD using datapackage metadata."""
    click.echo(f"Creating CSV from {jsonld}")
    create_csv_from_jsonld(jsonld, datapackage, output)
    click.echo(f"✓ Created: {output}")


def create_jsonld_framed(
    ttl: Path,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
    frame_only: bool,
    batch_size: int,
) -> None:
    """Create JSON-LD framed representation from TTL and frame."""
    frame_data = yaml.safe_load(frame.read_text(encoding="utf-8"))
    if not output.parent.exists():
        raise FileNotFoundError(
            f"Output directory {output.parent} does not exist"
        )

    from tools.projector import frame_context_fields, project, select_fields

    callbacks = []
    if frame_only:
        click.echo(
            "⚠️  --frame-only is set: "
            "the framed JSON-LD will only include fields "
            "defined in the frame context, even if they are present in the original RDF graph."
        )

        def filter_fields_cb(framed):
            return select_fields(
                framed, {"@type", *frame_context_fields(frame_data)}
            )

        callbacks.append(filter_fields_cb)
    framed = project(
        frame_data,
        ttl,
        callbacks=callbacks,
        batch_size=batch_size,
    )
    with output.open("w", encoding="utf-8") as f:
        yaml.safe_dump(framed, f, allow_unicode=True, indent=2)


def create_datapackage_metadata(
    ttl: Path, frame: Path, vocabulary_uri: str, output: Path, lang: str
) -> None:
    """Create Frictionless Data Package metadata stub."""
    raise NotImplementedError("create_datapackage_metadata not yet implemented")


def create_oas_spec(jsonld: Path, datapackage: Path, output: Path) -> None:
    """Create OpenAPI specification from framed JSON-LD."""
    raise NotImplementedError("create_oas_spec not yet implemented")


def create_csv_from_jsonld(
    jsonld: Path, datapackage: Path, output: Path
) -> None:
    """Create CSV file from framed JSON-LD using datapackage metadata."""
    raise NotImplementedError("create_csv_from_jsonld not yet implemented")


if __name__ == "__main__":
    cli()
