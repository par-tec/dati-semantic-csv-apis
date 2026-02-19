import json
from operator import itemgetter
from pathlib import Path

import pytest
import yaml
from rdflib.compare import IsomorphicGraph

from tools.projector import frame_context_fields, project, select_fields
from tools.utils import IGraph

TESTDIR = Path(__file__).parent.parent
testcases_yaml = TESTDIR / "testcases.yaml"
TESTCASES = yaml.safe_load(testcases_yaml.read_text())["testcases"]

ASSET = TESTDIR.parent / "assets" / "controlled-vocabularies"
vocabularies = list(ASSET.glob("**/*.ttl"))


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
    framed = project(
        frame, data, callbacks=[lambda framed: select_fields(framed, selected_fields)]
    )
    graph = framed["@graph"]

    for item in graph:
        item_fields = set(item.keys())
        assert item_fields <= selected_fields, (
            f"Item fields {item_fields} are not a subset of selected fields {selected_fields}"
        )

    assert graph == expected_payload, "Projected data does not match expected payload"


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
    framed = project(
        frame, data, callbacks=[lambda framed: select_fields(framed, selected_fields)]
    )
    statistics = framed.pop("statistics", {})
    assert statistics, "Statistics should be present in the framed data"

    framed_graph: IsomorphicGraph = IGraph.parse(
        data=json.dumps(framed), format="application/ld+json"
    )

    original_graph: IsomorphicGraph = IGraph.parse(data=data, format="text/turtle")
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
    framed = project(
        frame,
        vocabulary_ttl,
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
    data.write_text(yaml.safe_dump(framed))
