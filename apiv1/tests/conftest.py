import json
import sqlite3
from pathlib import Path

import pytest

from tests.harness import ATECO_SPEC, DATADIR
from tools.store import APIStore

CATALOG_ENTRY = {
    "vocabulary_uri": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
    "agency_id": "istat",
    "key_concept": "ateco-2025",
    "openapi": ATECO_SPEC,
    "catalog": {
        "about": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
        "title": "Ateco 2025 - Classificazione delle attività economiche",
        "description": "Classificazione statistica delle attività finalizzata all’elaborazione di statistiche ufficiali, aventi per oggetto i fenomeni relativi alla partecipazione delle unità produttive ai processi economici. La classificazione è direttamente derivata da NACE Rev. 2.1 (Regolamento delegato (Ue) 2023/137 della Commissione che modifica il Regolamento (CE) n. 1893/2006 del Parlamento europeo e del Consiglio; rettifica n. 2024/90720). La classificazione Ateco 2025 comprende 1.290 sottocategorie, 920 categorie, raggruppate in 651 classi, 272 gruppi, 87 divisioni, 22 sezioni.\n    La struttura delle versioni precedenti è:\n    - Ateco 2007 1° rilascio: 996 categorie, raggruppate in 615 classi, 272 gruppi, 88 divisioni, 21 sezioni; negli anni la classificazione ha subito due aggiornamenti, uno nel 2021 l'altro nel 2022;\n    - Ateco 2002: 883 categorie, raggruppate in 514 classi, 224 gruppi, 62 divisioni, 17 sezioni, 16 sottosezioni;\n    - Ateco 1991: 874 categorie, raggruppate in 512 classi, 222 gruppi, 60 divisioni, 17 sezioni, 16 sottosezioni.",
        "hreflang": ["it"],
        "version": "versione 2025",
        "author": "https://w3id.org/italia/data/public-organization/ISTAT",
    },
}


@pytest.fixture
def sample_db():
    return (DATADIR / "harvest.db").as_posix()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "performance: mark tests intended for benchmarking or perf checks",
    )


@pytest.fixture
def single_entry_db(tmp_path: Path) -> str:
    db_path = tmp_path / "deleteme.db"

    with APIStore(db_path.as_posix()) as db:
        db.create_metadata_table()
        db.upsert_metadata(**CATALOG_ENTRY)
        db.update_vocabulary_table(
            agency_id="istat",
            key_concept="ateco-2025",
            rows=[
                {
                    "id": "A01",
                    "url": "https://example.com/vocabularies/test/A01",
                    "label": "Item A01",
                    "level": "1",
                    "_text": json.dumps(
                        {
                            "id": "A01",
                            "label": "Item A01",
                            "url": "https://example.com/vocabularies/test/A01",
                        }
                    ),
                }
            ],
        )
        db.create_fts_table()

    return db_path.as_posix()


@pytest.fixture
def broken_dataset_db(tmp_path: Path) -> str:
    db_path = tmp_path / "broken-harvest.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE _metadata (
            vocabulary_uuid TEXT PRIMARY KEY,
            vocabulary_uri TEXT NOT NULL,
            agency_id TEXT NOT NULL,
            key_concept TEXT NOT NULL,
            openapi TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX agency_id_key_concept_unique
        ON _metadata (agency_id, key_concept)
        """
    )
    conn.execute(
        "INSERT INTO _metadata VALUES (?, ?, ?, ?, ?)",
        (
            "missing-table-uuid",
            "https://example.com/vocabularies/broken",
            "agid",
            "broken-vocab",
            json.dumps(ATECO_SPEC),
        ),
    )
    conn.commit()
    conn.close()
    return db_path.as_posix()
