import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

import yaml

from tools.store import APIStore

log = logging.getLogger(__name__)


def sparql_query(
    sparql_url: str, query: str, format: str = "application/ld+json"
) -> bytes:
    params = {"query": query, "format": format}
    headers = {"Accept": format}

    # Build URL with query parameters
    url = f"{sparql_url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request) as response:
        response_data = cast(bytes, response.read())
        return response_data


class Catalog:
    """
    A class to represent a catalog of vocabularies, which can be loaded from a SPARQL endpoint.

    The catalog is represented as a JSON-LD graph, where each node represents a vocabulary scheme with its properties.

    The class provides methods to load the catalog from a SPARQL endpoint and to access the vocabulary schemes and their properties.
    """

    def __init__(self, sparql_url: str):
        self.sparql_url = sparql_url
        self._graph: dict[str, Any] | None = None

    @property
    def graph(self) -> dict[str, Any]:
        if self._graph is None:
            self._graph = sparql_query_vocabularies(self.sparql_url)
        assert self._graph is not None
        return self._graph

    def vocabularies(self) -> dict[str, Any]:
        """
        Return the list of vocabulary schemes in the catalog, with their properties.

        Each scheme is represented as a dictionary with keys such as 'concept', 'title', 'languages', 'description', 'type', 'version', and 'publisher'.
        """
        return self.graph

    def items(self):
        """
        Return the list of vocabulary schemes in the catalog, with their properties.

        Each scheme is represented as a dictionary with keys such as 'concept', 'title', 'languages', 'description', 'type', 'version', and 'publisher'.
        """
        return self.graph["@graph"] if "@graph" in self.graph else []

    def to_db(self, harvest_db: APIStore):
        """
        Store the catalog data into the harvest.db SQLite database.

        This method iterates over the vocabulary schemes in the catalog and stores their metadata and items into the database using the provided APIStore instance.
        """
        schemes = transform_sparql_to_linkset_items(self.graph, "")
        for _, scheme_data in schemes.items():
            agency_id = scheme_data["author"].split("/")[-1].lower()
            key_concept = scheme_data["_concept"]
            harvest_db.upsert_metadata(
                vocabulary_uri=scheme_data["about"],
                agency_id=agency_id,
                key_concept=key_concept,
                openapi={},  # Placeholder for the OpenAPI spec
                catalog=scheme_data,  # Store the catalog data as-is
            )

    def linkset(self, base_url: str) -> dict:
        """
        Return the catalog in RFC 9727 linkset format, with links to the API endpoints for each vocabulary scheme.

        Each item in the linkset includes properties such as 'href', 'about', 'title', 'description', 'hreflang', 'version', 'author', and relations like 'service-desc' and 'predecessor-version'.
        """
        schemes = self.items()
        # Build the linkset response
        linkset = [
            {
                "api-catalog": base_url,
                "anchor": base_url,
                "item": list(schemes.values()),
            }
        ]

        return {"linkset": linkset}


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


def transform_sparql_to_linkset_items(
    sparql_results: dict, base_url: str
) -> dict:
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
        predecessor_url = (
            f"https://schema.gov.it/api/vocabularies/{agency_id}/{concept}"
        )

        # URLs that could be built at runtime.
        api_url = f"{base_url}{agency_id}/{concept}"
        openapi_url = f"{api_url}/openapi.yaml"

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
    return schemes


def load_linkset_data(datafile: str) -> dict[str, Any]:
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
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX NDC: <https://w3id.org/italia/onto/NDC/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX at: <http://publications.europa.eu/resource/authority/file-type/>
        PREFIX : <http://github.com/par-tec/dati-semantic-csv-apis#>


        CONSTRUCT {
            # Required properties for API endpoint:
            ?scheme NDC:keyConcept ?keyConcept
            ; dcterms:rightsHolder ?publisher

            # Catalog properties for linkset:
            ; skos:prefLabel ?title
            ; dcterms:language ?languages
            ; dcterms:description ?description
            ; dcterms:type ?type
            ; owl:versionInfo ?version

            # Relation with the turtle download URL:
            ; :turtleDownloadUrl ?download_url
            .
        }
        WHERE {
            ?scheme
            NDC:keyConcept ?keyConcept
            ; dcterms:rightsHolder ?publisher
            ; skos:prefLabel ?title
            ; dcat:distribution ?distribution
            .
            ?distribution
                dcat:downloadURL ?download_url ;
                dcterms:format at:RDF_TURTLE .

            OPTIONAL {
                ?scheme dcterms:language ?languages .
            }
            OPTIONAL {
                ?scheme dcterms:description ?description .
            }
            OPTIONAL {
                ?scheme dcterms:type ?type .
            }
            OPTIONAL {
                ?scheme owl:versionInfo ?version .
            }

        }
        """
    response_data = sparql_query(
        sparql_url, query, format="application/ld+json"
    )
    response_text = response_data.decode("utf-8")
    return cast(dict[Any, Any], json.loads(response_text))
