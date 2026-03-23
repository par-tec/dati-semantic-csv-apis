import json
from collections import defaultdict
from pathlib import Path

import pytest
import yaml
from catalog.download import (
    sparql_query,
    sparql_query_vocabularies,
    transform_sparql_to_linkset,
)

CWD = Path(__file__).parent

API_BASE_URL = "https://schema.gov.it/api/vocabularies/v1/"
SPARQL_URL = "https://virtuoso-test-external-service-ndc-test.apps.cloudpub.testedev.istat.it/sparql"


def test_download():
    all_vocabularies = sparql_query(
        SPARQL_URL,
        """
        PREFIX NDC: <https://w3id.org/italia/onto/NDC/>

        CONSTRUCT {
        ?scheme
            NDC:keyConcept ?c;
            dcterms:rightsHolder ?publisher
        .
        }
        WHERE {
        ?scheme
             NDC:keyConcept ?c;
            dcterms:rightsHolder ?publisher
        .
        }
                    """,
    )
    json.loads(all_vocabularies).get("@graph", [])
    data = sparql_query_vocabularies(SPARQL_URL)
    data = {x["@id"] for x in data.get("@graph", [])}
    assert len(data) == 148

    raise pytest.skip("Support dcat and not only skos")


def test_transform_vocabularies_to_linkset():
    """
    Test that SPARQL vocabularies are correctly transformed into linkset format.

    This test validates the transformation of vocabulary data from SPARQL query results
    into the RFC 9727 linkset format used by the vocabularies API endpoint.
    """

    KNOWN_DUPLICATES = {"ateco-2007"}
    # Load test data from vocabularies.yamlld
    with open(CWD / "vocabularies.yamlld", encoding="utf-8") as f:
        sparql_results = yaml.safe_load(f)

    # Transform to linkset format
    result = transform_sparql_to_linkset(sparql_results, base_url=API_BASE_URL)

    VOCABULARIES_LINKSET_YAML = CWD / "vocabularies.linkset.yaml"
    yaml.safe_dump(
        result, open(VOCABULARIES_LINKSET_YAML, "w", encoding="utf-8")
    )
    # Validate structure
    assert "linkset" in result
    assert isinstance(result["linkset"], list)
    assert len(result["linkset"]) == 1

    linkset_item = result["linkset"][0]

    # Validate RFC 9727 api-catalog
    assert linkset_item["api-catalog"] == API_BASE_URL

    # Validate anchor
    assert linkset_item["anchor"] == API_BASE_URL

    # Validate items (RFC 6573)
    assert isinstance(linkset_item["item"], list)
    assert len(linkset_item["item"]) > 0

    # Validate first item structure
    first_item = linkset_item["item"][0]

    # RFC 8288 Web Linking fields
    assert "href" in first_item
    assert "title" in first_item

    # Check hreflang if present
    assert isinstance(first_item["hreflang"], list)

    # RFC 8631 service-desc
    assert isinstance(first_item["service-desc"], list)
    for service_desc in first_item["service-desc"]:
        assert service_desc["href"].startswith(API_BASE_URL)

        assert (
            service_desc["href"]
            == "https://schema.gov.it/api/vocabularies/v1/istat/ateco-2007/openapi.yaml"
        )
        assert "type" in service_desc

    # Custom fields - description is mandatory
    assert "description" in first_item, "Description is mandatory"
    assert isinstance(first_item["description"], str)

    # Validate all items have mandatory description field
    for item in linkset_item["item"]:
        assert "description" in item, (
            f"Description is mandatory but missing for {item['href']}"
        )
        assert isinstance(item["description"], str)

    # Each API should reference a unique scheme URI.
    item_by_href = defaultdict(list)
    for item in linkset_item["item"]:
        item_by_href[item["href"]].append(item)
    duplicates = {
        href: items for href, items in item_by_href.items() if len(items) > 1
    }
    for href, items in duplicates.items():
        if any(known_duplicate in href for known_duplicate in KNOWN_DUPLICATES):
            continue  # known duplicate
        if len(items) == 2:
            assert items[0] == items[1], (
                f"Duplicate href with different content: {href}"
            )
        else:
            raise ValueError(f"Duplicate href found: {yaml.safe_dump(items)}")
