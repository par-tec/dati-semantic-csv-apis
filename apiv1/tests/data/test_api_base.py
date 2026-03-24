"""Fast tests for the Vocabularies data API ASGI app."""

from pathlib import Path

import pytest
import yaml
from data.app import Config, create_app

from tests.harness import client_harness

TESTDIR = Path(__file__).parent.parent
ATECO_OAS = TESTDIR / "api" / "ateco-2025.oas3.yaml"
ATECO_SPEC = yaml.safe_load(ATECO_OAS.read_text())


def _config(harvest_db: str) -> Config:
    return Config(
        API_BASE_URL="https://schema.gov.it/api/vocabularies/v1/",
        HARVEST_DB=harvest_db,
    )


def test_get_vocabularies(single_entry_db):
    """
    When:

    - I GET /vocabularies

    Then:

    - Response contains a linkset with item: [ .. ]
    """
    with client_harness(create_app, _config(single_entry_db)) as (client, logs):
        response = client.get("/vocabularies")
        assert response.json() == {
            "linkset": [
                {
                    "anchor": "https://schema.gov.it/api/vocabularies/v1/",
                    "api-catalog": "https://schema.gov.it/api/vocabularies/v1/",
                    "count": 1,
                    "item": [
                        {
                            "about": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025",
                            "author": "https://w3id.org/italia/data/public-organization/ISTAT",
                            "description": "Classificazione statistica delle "
                            "attività finalizzata all’elaborazione "
                            "di statistiche ufficiali, aventi per "
                            "oggetto i fenomeni relativi alla "
                            "partecipazione delle unità produttive "
                            "ai processi economici. La "
                            "classificazione è direttamente "
                            "derivata da NACE Rev. 2.1 (Regolamento "
                            "delegato (Ue) 2023/137 della "
                            "Commissione che modifica il "
                            "Regolamento (CE) n. 1893/2006 del "
                            "Parlamento europeo e del Consiglio; "
                            "rettifica n. 2024/90720). La "
                            "classificazione Ateco 2025 comprende "
                            "1.290 sottocategorie, 920 categorie, "
                            "raggruppate in 651 classi, 272 gruppi, "
                            "87 divisioni, 22 sezioni.\n"
                            "    La struttura delle versioni "
                            "precedenti è:\n"
                            "    - Ateco 2007 1° rilascio: 996 "
                            "categorie, raggruppate in 615 classi, "
                            "272 gruppi, 88 divisioni, 21 sezioni; "
                            "negli anni la classificazione ha "
                            "subito due aggiornamenti, uno nel 2021 "
                            "l'altro nel 2022;\n"
                            "    - Ateco 2002: 883 categorie, "
                            "raggruppate in 514 classi, 224 gruppi, "
                            "62 divisioni, 17 sezioni, 16 "
                            "sottosezioni;\n"
                            "    - Ateco 1991: 874 categorie, "
                            "raggruppate in 512 classi, 222 gruppi, "
                            "60 divisioni, 17 sezioni, 16 "
                            "sottosezioni.",
                            "href": "https://schema.gov.it/api/vocabularies/v1//istat/ateco-2025",
                            "hreflang": ["it"],
                            "predecessor-version": [
                                {
                                    "href": "https://old.example.com/istat/ateco-2025"
                                }
                            ],
                            "service-desc": [
                                {
                                    "href": "https://schema.gov.it/api/vocabularies/v1//istat/ateco-2025/openapi.yaml",
                                    "type": "application/openapi+yaml",
                                }
                            ],
                            "service-meta": [
                                {
                                    "href": "https://w3id.org/italia/stat/controlled-vocabulary/economy/ateco-2025?output=application/ld+json",
                                    "type": "application/ld+json",
                                }
                            ],
                            "title": "Ateco 2025 - Classificazione delle attività "
                            "economiche",
                            "version": "versione 2025",
                        }
                    ],
                    "limit": 20,
                    "offset": 0,
                    "total_count": 1,
                }
            ]
        }


def test_get_single_item(single_entry_db):
    """The app should serve one known vocabulary item through the ASGI client."""
    with client_harness(create_app, _config(single_entry_db)) as (client, logs):
        response = client.get("/vocabularies/agid/ateco-2025/A01")

        assert any("Application startup complete" in log for log in logs)
        assert response.status_code == 200
        assert response.json() == {
            "id": "A01",
            "label": "Item A01",
            "url": "https://example.com/vocabularies/test/A01",
            "href": "https://schema.gov.it/api/vocabularies/v1/agid/ateco-2025/A01",
        }


def test_latin_header(single_entry_db):
    """Test that the API can handle latin1 headers."""
    with client_harness(
        create_app,
        _config(single_entry_db),
    ) as (client, _logs):
        response = client.get(
            "/status",
            headers={"X-Test-Header": "Café\x80"},
        )
        assert response.status_code == 200


def test_rejects_non_printable_query_parameter(single_entry_db) -> None:
    """Non-printable query parameter values should be rejected."""
    with client_harness(
        create_app,
        _config(single_entry_db),
    ) as (client, _logs):
        response = client.get(
            "/agid/ateco-2025",
            params={"label": "\u2008invalid"},
        )
        assert response.status_code == 400


@pytest.mark.skip(reason="Check why it happens.")
def test_missing_vocab_returns_404(
    broken_dataset_db,
) -> None:
    """Missing vocabulary tables should be reported as a sanitized 404 problem."""
    with client_harness(
        create_app,
        _config(broken_dataset_db),
    ) as (client, _logs):
        response = client.get("/vocabularies/agid/broken-vocab")

        assert response.status_code == 404
        assert (
            response.headers["content-type"].split(";")[0]
            == "application/problem+json"
        )
        body = response.json()
        assert body["title"] == "Not Found"
        assert body["status"] == 404
        assert body["detail"] == "The requested vocabulary was not found"
