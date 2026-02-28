import json
from operator import itemgetter

import pytest
import yaml
from rdflib.compare import IsomorphicGraph

from tests.constants import ASSETS, TESTCASES
from tools.base import TEXT_TURTLE
from tools.projector import frame_context_fields, select_fields
from tools.utils import IGraph
from tools.vocabulary import (
    APPLICATION_LD_JSON,
    UnsupportedVocabularyError,
    Vocabulary,
)

vocabularies = list(ASSETS.glob("**/*.ttl"))


@pytest.mark.parametrize(
    "data,frame,expected_payload",
    [itemgetter("data", "frame", "expected_payload")(x) for x in TESTCASES],
    ids=[x["name"] for x in TESTCASES],
)
def test_can_project_data(data, frame, expected_payload):
    """
    Given:
    - A framing context
    - An RDF graph

    When:
    - I create a framed API from the RDF graph and the framing context
    - I project the framed API to only include fields from the framing context

    Then:
    - I expect the projected API to only include fields from the framing context, or "@type"
    """
    selected_fields = {"@type", *frame_context_fields(frame)}
    vocabulary = Vocabulary(data)
    framed = vocabulary.project(
        frame,
        callbacks=[lambda framed: select_fields(framed, selected_fields)],
    )
    graph = framed["@graph"]

    for item in graph:
        item_fields = set(item.keys())
        assert item_fields <= selected_fields, (
            f"Item fields {item_fields} are not a subset of selected fields {selected_fields}"
        )

    assert graph == expected_payload, (
        "Projected data does not match expected payload"
    )


@pytest.mark.parametrize(
    "data,frame,expected_payload",
    [itemgetter("data", "frame", "expected_payload")(x) for x in TESTCASES],
    ids=[x["name"] for x in TESTCASES],
)
def test_can_validate_data(data, frame, expected_payload):
    """
    Given:

    - An RDF graph
    - A framing context
    - The framed API created from the RDF graph and the framing context
      applying this module process.

    When:
    - I interpret the framed API as a JSON-LD document and convert it back to RDF

    Then:
    - I expect the JSON-LD is a subgraph of the original RDF graph.
    """
    selected_fields = {"@type", *frame_context_fields(frame)}
    vocabulary = Vocabulary(data)
    framed = vocabulary.project(
        frame,
        callbacks=[lambda framed: select_fields(framed, selected_fields)],
    )
    statistics = framed.pop("statistics", {})
    assert statistics, "Statistics should be present in the framed data"

    framed_graph: IsomorphicGraph = IGraph.parse(
        data=json.dumps(framed), format=APPLICATION_LD_JSON
    )

    original_graph: IsomorphicGraph = IGraph.parse(
        data=data, format=TEXT_TURTLE
    )
    extra_triples = framed_graph - original_graph
    assert len(extra_triples) == 0, (
        f"Framed graph has more triples {len(extra_triples)} than the original RDF graph"
    )


@pytest.mark.asset
@pytest.mark.parametrize(
    "vocabulary_ttl",
    vocabularies,
    ids=[x.name for x in vocabularies],
)
def test_can_frame_assets(vocabulary_ttl):
    """
    Given:
    - A controlled vocabulary RDF graph
    - A framing context that selects preferred terms

    When:
    - I create a framed API from the RDF graph and the framing context

    Then:
    - I expect the framed API to only include preferred terms
    """
    frame_path = vocabulary_ttl.with_suffix(".frame.yamlld")
    if not frame_path.exists():
        pytest.skip(f"No framing context found for {vocabulary_ttl}")
    frame = yaml.safe_load(frame_path.read_text())

    selected_fields = {"@type", *frame_context_fields(frame)}
    vocabulary = Vocabulary(vocabulary_ttl)
    try:
        uri = vocabulary.uri()
    except UnsupportedVocabularyError:
        pytest.skip(f"Unsupported vocabulary in {vocabulary_ttl}")

    assert uri, f"Vocabulary URI should be present in {vocabulary_ttl}"

    framed = vocabulary.project(
        frame,
        callbacks=[lambda framed: select_fields(framed, selected_fields)],
    )
    graph = framed["@graph"]

    # If an URI is in the graph, it shouldn't be in the filtered items :)
    filtered_items = framed["statistics"]["filtered"]
    for id_ in (x["url"] for x in graph):
        if id_ in filtered_items:
            filtered_items.remove(id_)

    for item in graph:
        item_fields = set(item.keys())
        assert item_fields <= selected_fields, (
            f"Item fields {item_fields} are not a subset of selected fields {selected_fields}"
        )

    data = vocabulary_ttl.with_suffix(".data.yaml")
    data.write_text(yaml.safe_dump(framed, sort_keys=True))
