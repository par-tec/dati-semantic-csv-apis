"""
Commands for creating and validating JSON-LD artifacts.

- Create: JSON-LD framed representation from RDF vocabulary using a JSON-LD frame
- Validate: Verify framed JSON-LD is a subset of original RDF vocabulary (graph isomorphism check)
"""

import json
import logging
from pathlib import Path

import click
import yaml
from rdflib.compare import IsomorphicGraph

from tools.projector import frame_context_fields, select_fields
from tools.utils import IGraph
from tools.vocabulary import Vocabulary

log = logging.getLogger(__name__)


@click.group(name="jsonld")
def jsonld():
    """Commands for JSON-LD artifacts."""
    pass


@jsonld.command(name="create")
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
def create_command(
    ttl: Path,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
    frame_only: bool,
    batch_size: int,
):
    """
    Create JSON-LD framed representation from RDF vocabulary.

    If passed files do not exist,
    Click returns an error.
    """
    click.echo(f"Framing vocabulary {vocabulary_uri} from {ttl}")
    create_jsonld_framed(
        ttl, frame, vocabulary_uri, output, frame_only, batch_size
    )
    click.echo(f"✓ Created: {output}")


@jsonld.command(name="validate")
@click.option(
    "--ttl",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the original RDF vocabulary file in Turtle format",
)
@click.option(
    "--jsonld",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the JSON-LD framed file to validate",
)
@click.option(
    "--vocabulary-uri",
    type=str,
    required=True,
    help="URI of the vocabulary (ConceptScheme) to validate",
)
def validate_command(ttl: Path, jsonld: Path, vocabulary_uri: str):
    """
    Validate that JSON-LD framed representation is a subset of original RDF.

    Performs graph isomorphism check to ensure the framed JSON-LD contains
    only data present in the original RDF vocabulary.

    If passed files do not exist,
    Click returns an error.
    """
    click.echo(f"Validating JSON-LD {jsonld} against {ttl}")
    click.echo(f"Vocabulary URI: {vocabulary_uri}")

    try:
        validate_jsonld_subset(ttl, jsonld, vocabulary_uri)
        click.secho("✓ JSON-LD validation passed", fg="green")
    except Exception as e:
        click.secho(f"✗ JSON-LD validation failed: {e}", fg="red", err=True)
        raise click.Abort() from e


def create_jsonld_framed(
    ttl: Path,
    frame: Path,
    vocabulary_uri: str,
    output: Path,
    frame_only: bool,
    batch_size: int,
) -> None:
    """Create JSON-LD framed representation from TTL and frame."""
    # Click checks file existence.
    frame_data = yaml.safe_load(frame.read_text(encoding="utf-8"))

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
    log.debug(
        f"Creating framed JSON-LD with batch size {batch_size} and callbacks: {[cb.__name__ for cb in callbacks]}"
    )
    vocabulary: Vocabulary = Vocabulary(ttl)
    framed = vocabulary.project(
        frame_data,
        callbacks=callbacks,
        batch_size=batch_size,
    )
    log.debug(
        f"Framed JSON-LD created successfully with {len(framed.get('@graph', []))} items"
    )
    with output.open("w", encoding="utf-8") as f:
        yaml.safe_dump(framed, f, allow_unicode=True, indent=2)


def validate_jsonld_subset(
    ttl: Path, jsonld: Path, vocabulary_uri: str
) -> None:
    """
    Validate that JSON-LD framed representation is a subset of original RDF.

    If passed files do not exist,
    Click returns an error.

    Args:
        ttl: Path to original RDF vocabulary in Turtle format
        jsonld: Path to JSON-LD framed file
        vocabulary_uri: URI of the vocabulary to validate

    Raises:
        ValueError: If JSON-LD contains data not in original RDF
    """
    original_graph: IsomorphicGraph = IGraph.parse(
        source=ttl, format="text/turtle"
    )
    log.debug(f"Original RDF graph has {len(original_graph)} triples")

    if vocabulary_uri not in (str(s) for s in original_graph.subjects()):
        raise ValueError(
            f"Vocabulary URI {vocabulary_uri} not found in original RDF graph"
        )
    log.debug(f"Vocabulary URI {vocabulary_uri} found in original RDF graph")

    if not jsonld.exists():
        raise ValueError(f"JSON-LD framed file not found: {jsonld.absolute()}")

    #
    # These extra steps are needed to strip out
    #   any extra fields beyond `@context` and `@graph`.
    #
    with jsonld.open(encoding="utf-8") as f:
        framed_yamlld = yaml.safe_load(f)

    framed_graph: IsomorphicGraph = IGraph.parse(
        data=json.dumps(
            {
                "@context": framed_yamlld.get("@context", {}),
                "@graph": framed_yamlld.get("@graph", []),
            }
        ),
        format="application/ld+json",
    )
    log.debug(f"Framed JSON-LD graph has {len(framed_graph)} triples")

    extra_triples = framed_graph - original_graph
    if len(extra_triples) > 0:
        raise ValueError(
            f"Framed JSON-LD contains {len(extra_triples)} triples not present in original RDF vocabulary"
        )
