from pathlib import Path

import pytest
import yaml

from tests.constants import DATADIR, TESTCASES
from tools.base import JsonLDFrame
from tools.openapi import Apiable
from tools.store import APIStore

TESTCASES_YAML = Path(__file__).with_suffix(".yaml")
SEARCH_TESTCASES = yaml.safe_load(TESTCASES_YAML.read_text())["testcases"]


def _human_readable_row_factory(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row, strict=True))


@pytest.fixture
def sample_search_db(tmp_path):
    db_path = tmp_path / "harvest.db"
    base_snapshots = DATADIR / "snapshots" / "base"
    loaded_vocabularies = {}

    with APIStore(db_path.as_posix()) as db:
        db.create_metadata_table()
        for testcase in TESTCASES:
            oas3_yaml = base_snapshots / f"{testcase['name']}.oas3.yaml"
            if (
                not oas3_yaml.exists()
                or "data" not in testcase
                or "frame" not in testcase
            ):
                continue

            apiable = Apiable(testcase["data"], JsonLDFrame(testcase["frame"]))
            metadata = apiable.metadata()
            if metadata.agency_id is None or metadata.name is None:
                continue

            record_key = (metadata.agency_id, metadata.name)
            if record_key in loaded_vocabularies:
                continue

            db.upsert_metadata(
                vocabulary_uri=apiable.uri(),
                agency_id=metadata.agency_id,
                key_concept=metadata.name,
                openapi=yaml.safe_load(oas3_yaml.read_text()),
                catalog=apiable.catalog_entry(),
            )
            loaded_vocabularies[record_key] = {
                "agency_id": metadata.agency_id,
                "key_concept": metadata.name,
            }

        db.create_fts_table()

    return db_path.as_posix(), loaded_vocabularies


@pytest.fixture
def apistore(sample_search_db):
    db_path, loaded_vocabularies = sample_search_db
    with APIStore(db_path, row_factory=_human_readable_row_factory) as db:
        yield db, loaded_vocabularies


@pytest.mark.parametrize(
    "testcase",
    SEARCH_TESTCASES,
    ids=[tc["id"] for tc in SEARCH_TESTCASES],
)
def test_search_metadata(apistore, testcase):
    db, _ = apistore
    search = testcase["search"]
    expected = testcase["results"]

    results = db.search_metadata(**search)

    assert len(results) == len(expected)
    for result, exp in zip(results, expected, strict=True):
        assert result["agency_id"] == exp["agency_id"]
        assert result["key_concept"] == exp["key_concept"]
