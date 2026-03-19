"""CLI entrypoint for harvest commands."""

import json
import logging
from pathlib import Path

import click

from tools.harvest import VocabularyRepository
from tools.harvest.catalog import Catalog

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
SPARQL_URL = "https://schema.gov.it/sparql"


@click.group()
@click.option("--sparql-url", default=SPARQL_URL)
@click.pass_context
def harvest(ctx: click.Context, sparql_url: str) -> None:
    ctx.obj = Catalog(sparql_url)


@harvest.command("list")
@click.pass_obj
def list_command(catalog: Catalog) -> None:
    click.echo(json.dumps(catalog.vocabularies(), ensure_ascii=False, indent=2))


@harvest.command()
@click.argument("agency_id")
@click.argument("key_concept")
@click.option(
    "--download-dir",
    "download_dir",
    "-d",
    type=click.Path(path_type=Path),
    required=True,
)
@click.pass_obj
def download(
    catalog: Catalog, agency_id: str, key_concept: str, download_dir: Path
) -> None:
    item = next(
        node
        for node in catalog.vocabularies()["@graph"]
        if Path(node["rightsHolder"]).name.lower() == agency_id.lower()
        and node["keyConcept"] == key_concept
    )
    repo = VocabularyRepository(
        download_url=item["turtleDownloadUrl"],
        key_concept=item["keyConcept"],
        rights_holder=item["rightsHolder"],
        vocabulary_uri=item["@id"],
    )

    download_dir.mkdir(parents=True, exist_ok=True)
    log.info("Downloading vocabulary data from %s", repo.download_url)
    try:
        repo.download(download_dir)
    except Exception as e:
        log.error("Failed to download vocabulary data: %s", e)
    click.echo(download_dir.as_posix())


if __name__ == "__main__":
    harvest()
