"""Shared SQLite schema helpers for ``harvest.db``.

This module is intentionally stdlib-only so both ingestion and API code can
reuse the same DDL without importing heavier project dependencies.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft7Validator, validate

log = logging.getLogger(__name__)
METADATA_TABLE = "_metadata"
METADATA_UNIQUE_INDEX = "agency_id_key_concept_unique"

METADATA_REQUIRED_COLUMNS = (
    "vocabulary_uuid",
    "agency_id",
    "key_concept",
    "openapi",
)

CREATE_METADATA_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS _metadata (
    vocabulary_uuid TEXT PRIMARY KEY,
    vocabulary_uri TEXT NOT NULL,
    agency_id TEXT NOT NULL,
    key_concept TEXT NOT NULL,
    openapi TEXT NOT NULL,
    catalog TEXT NOT NULL
)
"""

CREATE_METADATA_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS agency_id_key_concept_unique
ON _metadata (agency_id, key_concept)
"""

FTS_TABLE = "_metadata_fts"

# Consider tweaking `tokenize` option.
CREATE_FTS_TABLE_SQL = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE}
USING fts5(title, description);
"""

POPULATE_FTS_TABLE_SQL = f"""
INSERT INTO {FTS_TABLE}(rowid, title, description)
SELECT rowid,
       json_extract(openapi, '$.info.title'),
       json_extract(openapi, '$.info.description')
FROM _metadata
"""

DELETE_FTS_TABLE_CONTENT_SQL = f"""
DELETE FROM {FTS_TABLE}
"""


def build_vocabulary_uuid(
    agency_id: str,
    key_concept: str,
) -> str:
    """Build a stable vocabulary UUID.

    Hash ``agency_id|key_concept`` after normalization.
    """
    assert isinstance(agency_id, (str,))
    assert isinstance(key_concept, (str,))

    normalized_agency_id = (agency_id or "").strip().lower()
    normalized_key_concept = (key_concept or "").strip()
    if normalized_agency_id and normalized_key_concept:
        return sha256(
            f"{normalized_agency_id}|{normalized_key_concept}".encode()
        ).hexdigest()

    raise ValueError("Both agency_id and key_concept must be non-empty strings")


def has_unique_index_on_agency_key(cursor: sqlite3.Cursor) -> bool:
    """Return True when a unique index exists on (_metadata.agency_id, key_concept)."""
    for index in cursor.execute("PRAGMA index_list(_metadata)").fetchall():
        index_name = index[1]
        is_unique = bool(index[2])
        if not is_unique:
            continue

        index_columns = tuple(
            row[2]
            for row in cursor.execute(
                f'PRAGMA index_info("{index_name}")'
            ).fetchall()
        )
        if index_columns == ("agency_id", "key_concept"):
            return True

    return False


class APIStore:
    """Access layer for API payloads stored in harvest.db metadata and tables."""

    def __init__(
        self,
        sqlite_path: str,
        *,
        read_only: bool = False,
        check_same_thread: bool = True,
    ):
        self.sqlite_path = sqlite_path
        self.read_only = read_only
        self.check_same_thread = check_same_thread
        self.connection: sqlite3.Connection | None = None

    @staticmethod
    def _quoted_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def __enter__(self) -> APIStore:
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> sqlite3.Connection:
        if self.connection is None:
            database_path = self.sqlite_path
            connect_kwargs: dict[str, Any] = {
                "check_same_thread": self.check_same_thread,
            }
            if self.read_only:
                database_path = (
                    f"{Path(self.sqlite_path).resolve().as_uri()}?mode=ro"
                )
                connect_kwargs["uri"] = True
            self.connection = sqlite3.connect(database_path, **connect_kwargs)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def create_metadata_table(self) -> None:
        conn = self.connect()
        conn.execute(CREATE_METADATA_TABLE_SQL)
        conn.execute(CREATE_METADATA_UNIQUE_INDEX_SQL)
        conn.commit()

    def create_fts_table(self) -> None:
        """Create and populate the FTS5 index on openapi title/description."""
        conn = self.connect()
        conn.execute(CREATE_FTS_TABLE_SQL)
        # Keep it safe across repeated calls (eg request-time refresh).
        conn.execute(DELETE_FTS_TABLE_CONTENT_SQL)
        conn.execute(POPULATE_FTS_TABLE_SQL)
        conn.commit()

    def search_metadata(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[sqlite3.Row]:
        """Full-text search over openapi ``info.title`` and ``info.description``.

        Returns ``_metadata`` rows ranked by FTS5 relevance (best match first).
        Common FTS5 query syntax is supported: ``term``, ``term1 term2``,
        ``"exact phrase"``, ``term*`` (prefix), ``term1 OR term2``.
        """
        conn = self.connect()
        qp = {}
        # Ensure query respects FTS5 syntax.
        query = re.sub('[^a-zA-Z0-9*" ]', " ", query).strip() if query else ""

        if query:
            qp["query"] = query
            q = f"""
                    SELECT m.*
                    FROM _metadata m
                    JOIN {FTS_TABLE} f ON f.rowid = m.rowid
                    WHERE {FTS_TABLE} MATCH :query
                    ORDER BY rank
            """
        else:
            q = "SELECT * FROM _metadata WHERE 1=1 "

        if limit:
            qp["limit"] = str(limit)
            q += " LIMIT :limit "
        if offset:
            qp["offset"] = str(offset)
            q += " OFFSET :offset "

        return cast(
            list[sqlite3.Row],
            conn.execute(
                q,
                qp,
            ).fetchall(),
        )

    def validate_metadata_schema(self) -> None:
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (METADATA_TABLE,),
        )
        if not cursor.fetchone():
            raise ValueError(f"The is missing required {METADATA_TABLE} table")

        cursor.execute(f"PRAGMA table_info({METADATA_TABLE})")
        table_info = {row[1]: row for row in cursor.fetchall()}
        missing_columns = set(METADATA_REQUIRED_COLUMNS).difference(table_info)
        if missing_columns:
            raise ValueError(
                f"The {METADATA_TABLE} table is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        if table_info["vocabulary_uuid"][5] != 1:
            raise ValueError(
                "The _metadata.vocabulary_uuid must be a primary key"
            )

        if not has_unique_index_on_agency_key(cursor):
            raise ValueError(
                "The _metadata table is missing required unique index on (agency_id, key_concept)"
            )

    def validate_metadata_content(self) -> None:
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM _metadata WHERE agency_id IS NULL OR key_concept IS NULL"
        )
        if cursor.fetchone()[0] > 0:
            raise ValueError(
                "The _metadata table has null values in agency_id or key_concept columns"
            )

        for row in cursor.execute(f"SELECT openapi FROM {METADATA_TABLE}"):
            openapi = yaml.safe_load(row[0])
            validate(instance=openapi, schema=Draft7Validator.META_SCHEMA)

    def validate_integrity(self) -> bool:
        """Run ``PRAGMA integrity_check`` and return True when SQLite reports ``ok``."""
        conn = self.connect()
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row) and row[0] == "ok"

    def upsert_metadata(
        self,
        vocabulary_uri: str,
        agency_id: str,
        key_concept: str,
        openapi: dict[str, Any],
        catalog: dict[str, Any],
        *,
        commit: bool = True,
    ) -> None:
        vocabulary_uuid = self._table_name(agency_id, key_concept)
        conn = self.connect()
        conn.execute(
            """
            INSERT INTO _metadata (
                vocabulary_uuid,
                vocabulary_uri,
                agency_id,
                key_concept,
                openapi,
                catalog
            ) VALUES (:vocabulary_uuid, :vocabulary_uri, :agency_id, :key_concept, :openapi, :catalog)
            ON CONFLICT(vocabulary_uuid) DO UPDATE SET
                vocabulary_uri = excluded.vocabulary_uri,
                agency_id = excluded.agency_id,
                key_concept = excluded.key_concept,
                openapi = CASE
                    WHEN excluded.openapi = '{}' THEN _metadata.openapi
                    ELSE excluded.openapi
                END,
                catalog = CASE
                    WHEN excluded.catalog = '{}' THEN _metadata.catalog
                    ELSE excluded.catalog
                END
            """,
            {
                "vocabulary_uuid": vocabulary_uuid,
                "vocabulary_uri": vocabulary_uri,
                "agency_id": agency_id,
                "key_concept": key_concept,
                "openapi": json.dumps(openapi),
                "catalog": json.dumps(catalog),
            },
        )
        if commit:
            conn.commit()

    @staticmethod
    def _table_name(agency_id: str, key_concept: str) -> str:
        """Return the physical SQLite table name for a vocabulary."""
        return build_vocabulary_uuid(agency_id, key_concept)

    def get_metadata(
        self,
        agency_id: str,
        key_concept: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> sqlite3.Row | None:
        conn = self.connect()
        return cast(
            sqlite3.Row | None,
            conn.execute(
                "SELECT * FROM _metadata WHERE agency_id = ? AND key_concept = ?",
                (agency_id, key_concept),
            ).fetchone(),
        )

    def update_vocabulary_table(
        self,
        agency_id: str,
        key_concept: str,
        rows: list[dict[str, Any]],
    ) -> None:
        conn = self.connect()
        vocabulary_uuid = self._table_name(agency_id, key_concept)
        quoted_table_name = self._quoted_identifier(vocabulary_uuid)
        conn.execute(f"DROP TABLE IF EXISTS {quoted_table_name}")

        columns = ["id", "url", "label", "level", "_text"]
        quoted_columns = [self._quoted_identifier(column) for column in columns]
        column_defs = ", ".join(f"{column} TEXT" for column in quoted_columns)
        if not rows:
            conn.execute(f"CREATE TABLE {quoted_table_name} ({column_defs})")
            conn.commit()
            return

        placeholders = ", ".join("?" for _ in columns)
        insert_columns = ", ".join(quoted_columns)

        conn.execute(f"CREATE TABLE {quoted_table_name} ({column_defs})")
        conn.executemany(
            f"INSERT INTO {quoted_table_name} ({insert_columns}) VALUES ({placeholders})",
            [tuple(row.get(column) for column in columns) for row in rows],
        )
        conn.commit()

    def get_vocabulary_item_by_id(
        self, agency_id: str, key_concept: str, item_id: str
    ) -> dict[str, Any] | None:
        conn = self.connect()
        vocabulary_uuid = self._table_name(agency_id, key_concept)
        quoted_table_name = self._quoted_identifier(vocabulary_uuid)
        try:
            row = cast(
                sqlite3.Row | None,
                conn.execute(
                    f"SELECT _text FROM {quoted_table_name} WHERE id = ?",
                    (item_id,),
                ).fetchone(),
            )
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.info(
                    "Vocabulary table %s not found for agency_id=%s, key_concept=%s",
                    quoted_table_name,
                    agency_id,
                    key_concept,
                )
                return None
            raise
        if row is None:
            return None
        payload = json.loads(row["_text"])
        return (
            cast(dict[str, Any], payload) if isinstance(payload, dict) else None
        )

    def get_vocabulary_dataset(
        self,
        agency_id: str,
        key_concept: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        conn = self.connect()
        vocabulary_uuid = self._table_name(agency_id, key_concept)
        quoted_table_name = self._quoted_identifier(vocabulary_uuid)

        params = params or {}
        qs = f"SELECT _text FROM {quoted_table_name} WHERE 1=1 "
        query_params: dict[str, Any] = {}

        if params.get("cursor", ""):
            query_params |= {"cursor": params["cursor"]}
            qs += " AND id > :cursor "

        if "limit" in params:
            query_params |= {"limit": params["limit"]}
            qs += " LIMIT :limit "

        log.info("Executing SQL query %s with params %s", qs, query_params)
        try:
            rows = cast(
                list[sqlite3.Row],
                conn.execute(qs, query_params).fetchall(),
            )
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                log.info(
                    "Vocabulary table %s not found for agency_id=%s, key_concept=%s",
                    quoted_table_name,
                    agency_id,
                    key_concept,
                )
                return []
            raise

        return [json.loads(row["_text"]) for row in rows]

    @staticmethod
    def _remove_jsonld_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: APIStore._remove_jsonld_keys(v)
                for k, v in obj.items()
                if not k.startswith("@")
            }
        if isinstance(obj, list):
            return [APIStore._remove_jsonld_keys(item) for item in obj]
        return obj

    @staticmethod
    def jsonld_item_to_row(item: dict[str, Any]) -> dict[str, Any]:
        """Convert a JSON-LD item to a DB row dict.

        - Strips keys starting with ``@`` recursively.
        - Adds ``_text`` with the JSON serialisation of the cleaned item
          (``ensure_ascii=False`` to preserve non-ASCII labels).
        - Drops any value that is not a JSON primitive (int, float, bool,
          str, None) so the row can be inserted directly into SQLite columns.
        """
        sanitized = APIStore._remove_jsonld_keys(item)
        _text = json.dumps(sanitized, ensure_ascii=False)
        return {
            k: v
            for k, v in {**sanitized, "_text": _text}.items()
            if isinstance(v, (int, float, bool, str, type(None)))
        }

    def update_vocabulary_from_jsonld(
        self,
        agency_id: str,
        key_concept: str,
        graph: list[dict[str, Any]],
    ) -> None:
        """Serialize *graph* items to DB rows and write the vocabulary table."""
        rows = [self.jsonld_item_to_row(item) for item in graph]
        self.update_vocabulary_table(agency_id, key_concept, rows)

    def get_vocabulary_jsonld(
        self,
        agency_id: str,
        key_concept: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:  # type: ignore
        """Return a JsonLD dict ``{"@context": context, "@graph": [...]}``."""
        return {
            "@context": context,
            "@graph": self.get_vocabulary_dataset(agency_id, key_concept),
        }
