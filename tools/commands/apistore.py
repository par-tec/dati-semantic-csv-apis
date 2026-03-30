"""
Commands for creating and validating an APIStore SQLite database.

- create: populate a SQLite database from a TTL vocabulary and an OAS spec
- validate: check that the database schema and content are valid
"""

import logging
from pathlib import Path

import click
import yaml

from tools.base import JsonLDFrame

log = logging.getLogger(__name__)


@click.group(name="apistore")
def apistore():
    """Commands for APIStore SQLite databases."""
    pass


@apistore.command(name="create")
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
    required=False,
    help="Path to an already-framed JSON-LD data file; skips framing when provided",
)
@click.option(
    "--oas",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the OpenAPI specification file (provides framing context and is stored in _metadata)",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    required=True,
    help="Output path for the SQLite database",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Overwrite output file if it already exists.",
)
def create_command(
    ttl: Path,
    jsonld: Path | None,
    oas: Path,
    output: Path,
    force: bool,
):
    """Create an APIStore SQLite database from a TTL vocabulary and OAS spec.

    The frame is derived from the OAS spec's x-jsonld-context/x-jsonld-type.
    When --jsonld is provided the pre-framed data is stored directly;
    otherwise the TTL is framed on the fly.
    """
    if output.exists():
        if not force:
            click.secho(
                f"✗ Error: Output file {output} already exists. Use --force/-f to overwrite.",
                fg="red",
                err=True,
            )
            raise click.Abort()
        log.debug("Overwriting existing file: %s", output)

    create_apistore(ttl, jsonld, oas, output)
    click.echo(f"✓ Created: {output}")


def _frame_from_oas(oas_spec: dict) -> JsonLDFrame:
    """Reconstruct a JsonLDFrame from the x-jsonld-* extensions in an OAS spec."""
    item_schema = oas_spec["components"]["schemas"]["Item"]
    frame: dict = {"@context": item_schema["x-jsonld-context"]}
    if "x-jsonld-type" in item_schema:
        frame["@type"] = item_schema["x-jsonld-type"]
    return JsonLDFrame(frame)


def create_apistore(
    ttl: Path,
    jsonld: Path | None,
    oas: Path,
    output: Path,
) -> None:
    """Populate an APIStore SQLite database.

    The JSON-LD frame is derived from the OAS spec (x-jsonld-context,
    x-jsonld-type).  When jsonld is provided the pre-framed data is used
    directly; otherwise the TTL is framed via create_api_data().

    Args:
        ttl: Path to RDF Turtle file (always required — source of vocabulary metadata)
        jsonld: Path to already-framed JSON-LD file (optional)
        oas: Path to OpenAPI specification file
        output: Output path for the SQLite database
    """
    from tools.openapi import Apiable

    oas_spec = yaml.safe_load(oas.read_text(encoding="utf-8"))
    frame_data = _frame_from_oas(oas_spec)

    apiable = Apiable(rdf_data=ttl, frame=frame_data, format="text/turtle")

    if jsonld is not None:
        log.debug("Using pre-framed JSON-LD data from: %s", jsonld)
        data = yaml.safe_load(jsonld.read_text(encoding="utf-8"))
    else:
        log.debug("Framing TTL data from: %s", ttl)
        data = apiable.create_api_data()

    apiable.to_db(data=data, datafile=output, force=False, openapi=oas_spec)
    log.info("APIStore database created: %s", output)


def _resolve_db_sources(
    sources: tuple[str, ...],
    skip_not_found: bool,
    tmpdir: Path,
) -> list[Path]:
    """Resolve a mix of local paths and HTTPS URLs to local Path objects.

    For each source:
    - Local path/directory: expanded as before.
    - HTTPS URL: HEAD first; download on 200, skip or fail on 404.

    Each URL is downloaded into its own subdirectory of tmpdir to avoid
    filename collisions across different remote sources.

    Returns list of resolved .db Paths.
    """
    import urllib.error
    import urllib.request

    resolved: list[Path] = []

    for idx, source in enumerate(sources):
        if source.startswith("https://") or source.startswith("http://"):
            url = source
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req) as resp:
                    status = resp.status
            except urllib.error.HTTPError as e:
                status = e.code

            if status == 404:
                msg = f"Resource not found (404): {url}"
                if skip_not_found:
                    log.warning("Skipping: %s", msg)
                    continue
                click.secho(f"✗ {msg}", fg="red", err=True)
                raise click.Abort()

            if status != 200:
                msg = f"Unexpected HTTP {status} for: {url}"
                if skip_not_found:
                    log.warning("Skipping: %s", msg)
                    continue
                click.secho(f"✗ {msg}", fg="red", err=True)
                raise click.Abort()

            filename = url.rsplit("/", 1)[-1] or "downloaded.db"
            dest = tmpdir / str(idx) / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            log.debug("Downloading %s -> %s", url, dest)
            urllib.request.urlretrieve(url, dest)
            resolved.append(dest)

        else:
            local = Path(source).resolve()
            if local.is_dir():
                resolved.extend(
                    f
                    for f in local.glob("**/*.db")
                    if f.with_suffix(".ttl").exists()
                )
                log.debug("Collecting from directory: %s", local)
            else:
                resolved.append(local)

    return resolved


@apistore.command(name="collect")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    required=True,
    help="Output path for the aggregate SQLite database",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Overwrite output file if it already exists.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    default=False,
    help="Ignore 404 / missing URLs instead of failing.",
)
@click.argument("sources", nargs=-1)
def collect_command(
    output: Path, force: bool, skip_not_found: bool, sources: tuple[str, ...]
):
    """Merge multiple APIStore databases into a single aggregate database.

    SOURCES can be local file paths, directories, or HTTPS URLs pointing to .db files.
    """
    import tempfile

    from tools.harvest.collect import collect_databases

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            db_paths = _resolve_db_sources(
                sources, skip_not_found, Path(tmpdir)
            )
        except click.Abort:
            raise

        try:
            stats = collect_databases(output, db_paths, force=force)
            click.secho(
                f"✓ Collected into: {output} (processed: {stats['processed']}, skipped: {stats['skipped']}, metadata: {stats['metadata_count']}, tables copied: {stats['copied_tables']}, tables skipped: {stats['skipped_tables']})",
                fg="green",
            )
        except FileExistsError as e:
            click.secho(f"✗ {e}", fg="red", err=True)
            raise click.Abort() from e


@apistore.command(name="validate")
@click.option(
    "--db",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the APIStore SQLite database to validate",
)
@click.option(
    "--oas",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=Path
    ),
    required=True,
    help="Path to the OpenAPI specification file (provides components/schemas/Item for entry validation)",
)
def validate_command(db: Path, oas: Path):
    """Validate an APIStore SQLite database schema and content.

    Checks DB schema integrity and validates every stored entry against
    the JSON Schema in components/schemas/Item of the OAS spec.
    """
    click.echo(f"Validating apistore: {db}")

    try:
        total = validate_apistore(db, oas)
        click.secho(
            f"✓ APIStore validation passed ({total} entries validated)",
            fg="green",
        )
    except Exception as e:
        click.secho(f"✗ APIStore validation failed: {e}", fg="red", err=True)
        raise click.Abort() from e


def validate_apistore(db: Path, oas: Path) -> int:
    """Validate an APIStore SQLite database schema, content, and entry conformance.

    After structural checks, iterates every vocabulary in _metadata and
    validates each stored entry against components/schemas/Item in the OAS spec
    using validate_data_against_schema.

    Args:
        db: Path to the SQLite database
        oas: Path to the OpenAPI specification file

    Returns:
        Total number of validated entries

    Raises:
        ValueError: If the database or any entry is invalid
    """
    from tools.openapi import validate_data_against_schema
    from tools.store import APIStore

    oas_spec = yaml.safe_load(oas.read_text(encoding="utf-8"))
    item_schema = oas_spec["components"]["schemas"]["Item"]

    total_entries = 0
    all_errors: list[str] = []

    with APIStore(str(db), read_only=True) as store:
        store.validate_metadata_schema()
        store.validate_metadata_content()
        if not store.validate_integrity():
            raise ValueError("SQLite integrity check failed")

        for row in store.search_metadata(query=""):
            agency_id = row["agency_id"]
            key_concept = row["key_concept"]
            entries = store.get_vocabulary_dataset(agency_id, key_concept)
            total_entries += len(entries)

            is_valid, errors = validate_data_against_schema(
                entries, item_schema, limit_errors=10
            )
            if not is_valid:
                log.warning(
                    "%d schema error(s) in %s/%s",
                    len(errors),
                    agency_id,
                    key_concept,
                )
                all_errors.extend(
                    f"{agency_id}/{key_concept}[{e['index']}] "
                    f"{e['path']}: {e['message']}"
                    for e in errors
                )

    if all_errors:
        sample = "\n".join(all_errors[:10])
        raise ValueError(
            f"{len(all_errors)} entry validation error(s):\n{sample}"
        )

    log.info(
        "APIStore validation completed: %s (%d entries)", db, total_entries
    )
    return total_entries
