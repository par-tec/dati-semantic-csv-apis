"""
Model vocabulary endpoint according to the following expected payload:
"""

import json
import logging
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

import yaml

log = logging.getLogger(__name__)


def sparql_query_vocabularies(sparql_url: str) -> dict:
    """
    Query vocabularies from SPARQL endpoint using CONSTRUCT query.

    Returns JSON-LD representation of vocabulary schemes with their properties.
    Each scheme includes concept, title, languages, descriptions, type, version, and publisher.

    JSON-LD structure will be a graph with objects representing each vocabulary scheme.

    FIXME: this query does not find these URIs:
    {'https://w3id.org/italia/controlled-vocabulary/classifications-for-demanio/categoria_patrimoniale',
    'https://w3id.org/italia/controlled-vocabulary/classifications-for-learning/degree-classes',
    'https://w3id.org/italia/controlled-vocabulary/classifications-for-learning/grade',
    'https://w3id.org/italia/controlled-vocabulary/classifications-for-learning/programme-types/afam',
    'https://w3id.org/italia/controlled-vocabulary/classifications-for-learning/programme-types/mur',
    'https://w3id.org/italia/controlled-vocabulary/territorial-classifications/continents',
    'https://w3id.org/italia/controlled-vocabulary/territorial-classifications/countries',
    'https://w3id.org/italia/controlled-vocabulary/territorial-classifications/territorial-areas'}

    """

    query = """
        PREFIX ndc: <https://w3id.org/italia/onto/NDC/>
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        CONSTRUCT {
            ?scheme ndc:keyConcept ?concept .
            ?scheme skos:prefLabel ?title .
            ?scheme dct:language ?languages .
            ?scheme dct:description ?description .
            ?scheme dcterms:type ?type .
            ?scheme owl:versionInfo ?version .
            ?scheme dct:rightsHolder ?publisher .
        }
        WHERE {
            ?scheme ndc:keyConcept ?concept .
            ?scheme skos:prefLabel ?title .

            OPTIONAL {
                ?scheme dct:language ?languages .
            }
            OPTIONAL {
                ?scheme dct:description ?description .
            }
            OPTIONAL {
                ?scheme dcterms:type ?type .
            }
            OPTIONAL {
                ?scheme owl:versionInfo ?version .
            }
            OPTIONAL {
                ?scheme dct:rightsHolder ?publisher .
            }
        }
        """
    params = {"query": query, "format": "application/ld+json"}
    headers = {"Accept": "application/ld+json"}

    # Build URL with query parameters
    url = f"{sparql_url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request) as response:
        response_data = response.read().decode("utf-8")
        return cast(dict[Any, Any], json.loads(response_data))


ANY = object()


def get_value(val, lang=None):
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        if "@language" in val:
            if not lang:
                raise ValueError(
                    "Language must be specified for language-tagged values"
                )
            if lang == ANY:
                return val.get("@value")
            if lang != val["@language"]:
                raise ValueError(
                    f"Requested language {lang} does not match value language {val['@language']}"
                )
        return val.get("@value")
    if isinstance(val, list):
        for v in val:
            return get_value(v, lang)
    raise NotImplementedError("Value type not supported")


def get_languages(val: list):
    if isinstance(val, str):
        val = [val]

    for uri in val:
        for match, lang_code in [
            ("/ITA", "it"),
            ("/ENG", "en"),
            ("/DEU", "de"),
            ("/FRA", "fr"),
        ]:
            if uri.endswith(match):
                yield lang_code
                break
        else:
            raise NotImplementedError(
                f"Language mapping not implemented for {uri}"
            )


def transform_sparql_to_linkset(sparql_results: dict, base_url: str) -> dict:
    """
    Transform JSON-LD SPARQL results into RFC 9727 linkset format.

    Args:
        sparql_results: JSON-LD graph containing vocabulary schemes and their properties.
        base_url: Base URL for the API catalog.

    Returns:
        Dictionary in linkset format following RFC 9727 (api-catalog), RFC 8288 (Web Linking),
        RFC 8631 (service-desc), and RFC 5829 (predecessor-version).
    """
    # JSON-LD structure has @graph array containing all resources
    graph = sparql_results.get("@graph", [])

    if not base_url.endswith("/"):
        base_url += "/"
    # Group by scheme URI since JSON-LD may have multiple entries per scheme
    schemes = {}
    for node in graph:
        scheme_uri = node["@id"]
        agency_id = node["rightsHolder"].split("/")[-1].lower()
        concept = node["keyConcept"]
        api_url = f"{base_url}{agency_id}/{concept}"
        openapi_url = f"{api_url}/openapi.yaml"
        predecessor_url = (
            f"https://schema.gov.it/api/vocabularies/{agency_id}/{concept}"
        )

        if scheme_uri not in schemes:
            schemes[scheme_uri] = {
                "href": api_url,
                "about": scheme_uri,
                "title": get_value(node["prefLabel"], lang=ANY),
                "description": get_value(node["description"], lang=ANY),
                "hreflang": list(get_languages(node.get("language", []))),
                # "type": "application/json",
                "version": get_value(node["versionInfo"], lang=ANY),
                "author": node["rightsHolder"],
                "_vocabulary_type": node["type"],
                "_concept": node["keyConcept"],
            }

        scheme = schemes[scheme_uri]
        scheme["service-desc"] = [
            {"href": openapi_url, "type": "application/openapi+yaml"}
        ]
        scheme["service-meta"] = [
            {
                "href": f"{scheme_uri}?output=application/ld+json",
                "type": "application/ld+json",
            }
        ]
        scheme["predecessor-version"] = [
            {
                "href": predecessor_url,
            }
        ]

    # Build the linkset response
    linkset = [
        {
            "api-catalog": base_url,
            "anchor": base_url,
            "item": list(schemes.values()),
        }
    ]

    return {"linkset": linkset}


def load_linkset_data() -> dict[str, Any]:
    """
    Load linkset data from the configured YAML file.

    This function is called once at app initialization to load
    the vocabularies linkset into memory for efficient serving.

    Returns:
        The parsed linkset data structure.

    Raises:
        FileNotFoundError: If the data file cannot be found.
        yaml.YAMLError: If the YAML file is malformed.
    """
    datafile: str = os.getenv(
        "VOCABULARIES_DATAFILE", "vocabularies.linkset.yaml"
    )

    datafile_path = Path(datafile)

    if not datafile_path.is_file():
        if datafile_path.is_absolute():
            raise FileNotFoundError(f"Data file not found: {datafile_path}")
        # Try resolving relative path
        datafile_path = datafile_path.resolve()
        if not datafile_path.is_file():
            raise FileNotFoundError(f"Data file not found: {datafile_path}")

    log.info(f"Loading vocabularies dataset from: {datafile_path}")

    with open(datafile_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "linkset" not in data:
        raise ValueError(f"Invalid linkset format in {datafile_path}")

    log.info(
        f"Loaded {len(data.get('linkset', [{}])[0].get('item', []))} vocabulary items"
    )

    return data
