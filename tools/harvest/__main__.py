"""CLI entrypoint for harvest commands."""

import json
import logging
from pathlib import Path

import click

from tools.commands.jsonld import create_jsonld_framed
from tools.commands.openapi import create_oas_spec
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


@harvest.command()
@click.option(
    "-d", "--download-dir", type=click.Path(path_type=Path), required=True
)
@click.option("--default-frame", type=click.Path(path_type=Path), required=True)
@click.pass_obj
def pipeline(catalog: Catalog, download_dir: Path, default_frame: Path) -> None:
    for node in catalog.vocabularies()["@graph"]:
        agency_id = Path(node["rightsHolder"]).name.lower()
        key_concept = node["keyConcept"]
        node_dir = download_dir / agency_id / key_concept
        node_dir.mkdir(parents=True, exist_ok=True)
        repo = VocabularyRepository(
            download_url=node["turtleDownloadUrl"],
            key_concept=key_concept,
            rights_holder=node["rightsHolder"],
            vocabulary_uri=node["@id"],
        )
        if not repo.validate():
            log.error(
                "Skipping invalid repository for %s/%s", agency_id, key_concept
            )
            continue
        repo.download(node_dir)
        log.info("Downloaded %s/%s", agency_id, key_concept)

        ttl_path = node_dir / f"{key_concept}.ttl"
        frame_path = node_dir / f"{key_concept}.frame.yamlld"
        jsonld_output = node_dir / f"{key_concept}.data.yamlld"
        openapi_output = node_dir / f"{key_concept}.oas3.yaml"
        import shutil

        if not frame_path.exists():
            shutil.copy(default_frame, frame_path)
            log.info(
                "No frame found for %s/%s, copied default frame to %s",
                agency_id,
                key_concept,
                frame_path,
            )

        if not jsonld_output.exists():
            try:
                create_jsonld_framed(
                    ttl_path, frame_path, node["@id"], jsonld_output, True, 0
                )
                log.info(
                    "Created JSON-LD payload %s/%s", agency_id, key_concept
                )
            except Exception as e:
                (node_dir / "jsonld-error.log").write_text(str(e))
                log.error(
                    "Failed to create JSON-LD payload for %s/%s",
                    agency_id,
                    key_concept,
                )
                continue
        if not openapi_output.exists():
            try:
                create_oas_spec(
                    None, ttl_path, frame_path, node["@id"], openapi_output
                )
                log.info("Created OpenAPI spec %s/%s", agency_id, key_concept)
            except Exception as e:
                (node_dir / "jsonld-error.log").write_text(str(e))
                log.error(
                    "Failed to create OpenAPI spec for %s/%s",
                    agency_id,
                    key_concept,
                )


if __name__ == "__main__":
    harvest()
