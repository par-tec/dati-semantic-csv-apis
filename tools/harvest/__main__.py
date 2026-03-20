"""CLI entrypoint for harvest commands."""

import asyncio
import json
import logging
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import click

from tools.commands.jsonld import create_jsonld_framed
from tools.commands.openapi import create_oas_spec
from tools.harvest import VocabularyRepository
from tools.harvest.catalog import Catalog

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
SPARQL_URL = "https://schema.gov.it/sparql"


def _process_repository_node(
    node: dict[str, Any], download_dir: Path, default_frame: Path
) -> bool:
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
        return False

    try:
        repo.download(node_dir)
        log.info("Downloaded %s/%s", agency_id, key_concept)
    except Exception as exc:
        (node_dir / "download-error.log").write_text(str(exc))
        log.error("Failed to download %s/%s", agency_id, key_concept)
        return False

    ttl_path = node_dir / f"{key_concept}.ttl"
    frame_path = node_dir / f"{key_concept}.frame.yamlld"
    jsonld_output = node_dir / f"{key_concept}.data.yamlld"
    openapi_output = node_dir / f"{key_concept}.oas3.yaml"
    openapi_db = node_dir / f"{key_concept}.db"
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
            log.info("Created JSON-LD payload %s/%s", agency_id, key_concept)
        except Exception as exc:
            (node_dir / "jsonld-error.log").write_text(str(exc))
            log.error(
                "Failed to create JSON-LD payload for %s/%s",
                agency_id,
                key_concept,
            )
            return False
    import yaml

    from tools.base import JsonLDFrame

    apiable = None
    if not openapi_output.exists():
        try:
            apiable = create_oas_spec(
                None, ttl_path, frame_path, node["@id"], openapi_output
            )
            log.info("Created OpenAPI spec %s/%s", agency_id, key_concept)

        except Exception as exc:
            (node_dir / "openapi-error.log").write_text(str(exc))
            log.error(
                "Failed to create OpenAPI spec for %s/%s. See %s for details.",
                agency_id,
                key_concept,
                node_dir / "openapi-error.log",
            )
            return False
    from tools.openapi import Apiable

    if not openapi_db.exists():
        with jsonld_output.open("r", encoding="utf-8") as f:
            apiable = (
                Apiable(
                    rdf_data=ttl_path,
                    frame=JsonLDFrame.load(frame_path),
                )
                if not apiable
                else apiable
            )
            apiable.to_db(data=yaml.safe_load(f), datafile=openapi_db)
        log.info("Created OpenAPI DB %s/%s", agency_id, key_concept)
    return True


async def _run_async_pipeline(
    nodes: list[dict[str, Any]],
    download_dir: Path,
    default_frame: Path,
    workers: int,
) -> None:
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [
            loop.run_in_executor(
                pool,
                _process_repository_node,
                node,
                download_dir,
                default_frame,
            )
            for node in nodes
        ]
        results = await asyncio.gather(*futures)
    ok_count = sum(1 for result in results if result)
    log.info(
        "Async pipeline completed: %s processed, %s failed/skipped",
        ok_count,
        len(results) - ok_count,
    )


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


@harvest.command("serial-pipeline")
@click.option(
    "-d", "--download-dir", type=click.Path(path_type=Path), required=True
)
@click.option("--default-frame", type=click.Path(path_type=Path), required=True)
@click.pass_obj
def pipeline(catalog: Catalog, download_dir: Path, default_frame: Path) -> None:
    for node in catalog.vocabularies()["@graph"]:
        _process_repository_node(node, download_dir, default_frame)


@harvest.command("async-pipeline")
@click.option(
    "-d", "--download-dir", type=click.Path(path_type=Path), required=True
)
@click.option("--default-frame", type=click.Path(path_type=Path), required=True)
@click.option("--workers", type=int, default=4, show_default=True)
@click.pass_obj
def async_pipeline(
    catalog: Catalog, download_dir: Path, default_frame: Path, workers: int
) -> None:
    if workers < 1:
        raise click.BadParameter("workers must be >= 1", param_hint="--workers")

    nodes = catalog.vocabularies()["@graph"]
    asyncio.run(
        _run_async_pipeline(nodes, download_dir, default_frame, workers)
    )


@harvest.command("pipeline")
@click.option(
    "-d", "--download-dir", type=click.Path(path_type=Path), required=True
)
@click.option("--default-frame", type=click.Path(path_type=Path), required=True)
@click.option(
    "--mode",
    type=click.Choice(["serial", "parallel"], case_sensitive=False),
    default="serial",
    show_default=True,
)
@click.option("--workers", type=int, default=4, show_default=True)
@click.option("--limit", "-l", type=int, default=0, show_default=True)
@click.option(
    "-k",
    "--key-concept",
    type=str,
    required=False,
    help="Filter by key concept",
)
@click.pass_obj
def selectable_pipeline(
    catalog: Catalog,
    download_dir: Path,
    default_frame: Path,
    mode: str,
    workers: int,
    limit: int,
    key_concept: str | None,
) -> None:
    if mode == "serial":
        for i, node in enumerate(catalog.vocabularies()["@graph"]):
            log.info("Processing node %s/%s", i + 1, node["keyConcept"])
            if key_concept and key_concept not in node["keyConcept"]:
                continue
            if limit > 0 and i >= limit:
                break
            _process_repository_node(node, download_dir, default_frame)
        return

    if workers < 1:
        raise click.BadParameter("workers must be >= 1", param_hint="--workers")

    nodes = catalog.vocabularies()["@graph"]
    asyncio.run(
        _run_async_pipeline(nodes, download_dir, default_frame, workers)
    )


if __name__ == "__main__":
    harvest()
