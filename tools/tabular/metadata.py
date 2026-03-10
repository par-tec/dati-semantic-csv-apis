import logging
from pathlib import Path

import yaml
from jsonschema import validate
from rdflib import DCAT, DCTERMS

from tools.base import DATADIR
from tools.vocabulary import VocabularyMetadata

log = logging.getLogger(__name__)

# Define namespaces

DATAPACKAGE_SCHEMA_YAML = DATADIR / "datapackage.schema.json"
DATAPACKAGE_SCHEMA = yaml.safe_load(DATAPACKAGE_SCHEMA_YAML.read_text())


def create_datapackage(
    vocabulary: VocabularyMetadata,
    resources: list,
) -> dict:
    """
    Create a frictionless datapackage from JSON-LD RDF data.

    Args:
        vocabulary: VocabularyMetadata object containing the data
        resources: List of data resources to include in the datapackage
            (e.g., from a CSV file)
            by default, uses SKOS vocabulary terms, otherwise use others (e.g., DCTERMS, DCAT, OWL)
    Returns:
        dict: Frictionless datapackage dictionary
    """

    if not vocabulary:
        raise ValueError("Empty RDF graph")

    vocabulary_uri = vocabulary.identifier
    # XXX: Should we use conformsTo?
    # conformsTo = vocabulary.value(vocabulary_uri, DCTERMS.conformsTo)

    dcterms_identifier = vocabulary.get_identifier(
        DCTERMS.identifier, unique=True, required=True
    )
    # Map RDF properties to Frictionless datapackage fields
    datapackage = {
        "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
        "name": vocabulary.name,
        "id": dcterms_identifier or str(vocabulary_uri),
        "title": vocabulary.title or "",
        "sources": [
            {
                "path": str(vocabulary_uri),
            }
        ],
        "resources": resources or [],
    }

    # Add optional fields if present
    version = vocabulary.version
    if version:
        datapackage["version"] = version

    description = vocabulary.description
    if description:
        datapackage["description"] = description

    homepage = vocabulary.get_value(DCAT.accessURL)
    if homepage:
        datapackage["homepage"] = homepage

    created = vocabulary.get_value(DCTERMS.issued)
    if created:
        created = str(created)
        # Add time component if missing (datapackage spec requires date-time format).
        if len(created) == 10:
            created += "T00:00:00Z"
        datapackage["created"] = created

    keywords = vocabulary.get_values(DCAT.keyword)
    if keywords:
        keywords.sort()
        datapackage["keywords"] = keywords

    licenses = vocabulary.get_values(DCTERMS.license)
    if licenses:
        datapackage["licenses"] = licenses

    #
    # Since resources is required, we create a dummy resource if none is provided,
    #  just to validate the content we added.
    #
    validate_datapackage(
        datapackage
        | {
            "resources": [
                {
                    "name": "dummy",
                    "path": "dummy.csv",
                    "schema": {
                        "fields": [
                            {"name": "id", "type": "string"},
                            {"name": "label", "type": "string"},
                        ]
                    },
                }
            ]
        }
    )
    return datapackage


def validate_datapackage(datapackage: dict | Path) -> None:
    """Validate a datapackage dictionary against the frictionless datapackage JSON Schema."""

    datapackage_dict = (
        yaml.safe_load(datapackage.read_text())
        if isinstance(datapackage, Path)
        else datapackage
    )
    validate(datapackage_dict, DATAPACKAGE_SCHEMA)
