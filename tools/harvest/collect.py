import json
import logging
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from tools.store import APIStore

log = logging.getLogger(__name__)


def _quoted_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def collect_databases(
    aggregate_db: Path, db_paths: Iterable[Path], force: bool
) -> None:
    db_files = sorted(
        path for path in db_paths if path.resolve() != aggregate_db.resolve()
    )
    if not db_files:
        log.warning("No source .db files found for %s", aggregate_db)
        return

    if aggregate_db.exists() and not force:
        raise FileExistsError(
            f"{aggregate_db} already exists. Re-run with --force to overwrite."
        )

    if aggregate_db.exists() and force:
        aggregate_db.unlink()

    with APIStore(str(aggregate_db)) as aggregate_store:
        aggregate_store.create_metadata_table()
        aggregate_conn = aggregate_store.connect()

        processed = 0
        skipped = 0
        copied_tables = 0
        skipped_tables = 0

        for source_db in db_files:
            try:
                with APIStore(str(source_db), read_only=True) as source_store:
                    if not source_store.validate_integrity():
                        log.warning("Failed integrity check for %s", source_db)
                        skipped += 1
                        continue
                    source_store.validate_metadata_schema()
                    source_store.validate_metadata_content()
            except Exception as exc:
                log.warning("Skipping source DB %s: %s", source_db, exc)
                skipped += 1
                continue

            source_label = source_db.as_posix()
            attached = False
            try:
                aggregate_conn.execute("BEGIN")
                aggregate_conn.execute(
                    "ATTACH DATABASE ? AS source_db", (str(source_db),)
                )
                attached = True

                # Upsert all metadata rows from source DB into aggregate DB via APIStore.
                metadata_records = aggregate_conn.execute(
                    """
                    SELECT
                        vocabulary_uri,
                        agency_id,
                        key_concept,
                        openapi,
                        catalog
                    FROM source_db._metadata
                    """
                ).fetchall()
                for metadata in metadata_records:
                    aggregate_store.upsert_metadata(
                        vocabulary_uri=metadata["vocabulary_uri"],
                        agency_id=metadata["agency_id"],
                        key_concept=metadata["key_concept"],
                        openapi=json.loads(metadata["openapi"]),
                        catalog=json.loads(metadata["catalog"]),
                        commit=False,
                    )

                metadata_rows = aggregate_conn.execute(
                    "SELECT vocabulary_uuid FROM source_db._metadata"
                ).fetchall()

                for row in metadata_rows:
                    table_name = row[0]
                    if not table_name:
                        continue

                    source_table_exists = aggregate_conn.execute(
                        "SELECT 1 FROM source_db.sqlite_master WHERE type='table' AND name = ?",
                        (table_name,),
                    ).fetchone()
                    if not source_table_exists:
                        log.warning(
                            "Source table %s missing in %s",
                            table_name,
                            source_db,
                        )
                        continue

                    target_table_exists = aggregate_conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                        (table_name,),
                    ).fetchone()

                    quoted_table = _quoted_identifier(table_name)
                    if target_table_exists and not force:
                        skipped_tables += 1
                        log.info(
                            "Skipping existing table %s in aggregate DB (use --force to overwrite)",
                            table_name,
                        )
                        continue
                    if target_table_exists and force:
                        aggregate_conn.execute(
                            f"DROP TABLE IF EXISTS {quoted_table}"
                        )

                    aggregate_conn.execute(
                        f"CREATE TABLE {quoted_table} AS SELECT * FROM source_db.{quoted_table}"
                    )
                    copied_tables += 1

                aggregate_conn.commit()
                aggregate_conn.execute("DETACH DATABASE source_db")
                attached = False
                processed += 1
            except sqlite3.Error as exc:
                log.warning("Skipping source DB %s: %s", source_label, exc)
                aggregate_conn.rollback()
                if attached:
                    try:
                        aggregate_conn.execute("DETACH DATABASE source_db")
                    except sqlite3.Error:
                        pass
                skipped += 1

        metadata_count = aggregate_conn.execute(
            "SELECT COUNT(*) FROM _metadata"
        ).fetchone()[0]
        log.info(
            "Collect summary: %s processed, %s skipped, %s metadata rows, %s tables copied, %s tables skipped",
            processed,
            skipped,
            metadata_count,
            copied_tables,
            skipped_tables,
        )
