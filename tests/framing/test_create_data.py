import json
from contextlib import nullcontext
from operator import itemgetter

import pytest
import yaml
from rdflib.compare import IsomorphicGraph

from tests.constants import ASSETS, TESTCASES
from tests.harness import compare_data
from tools.base import TEXT_TURTLE, JsonLDFrame
from tools.projector import select_fields
from tools.utils import IGraph
from tools.vocabulary import (
    APPLICATION_LD_JSON,
    UnsupportedVocabularyError,
    Vocabulary,
)

vocabularies = list(ASSETS.glob("**/*.ttl"))


def _test_should_fail(obj):
    return isinstance(obj, type) and issubclass(obj, Exception)


@pytest.mark.parametrize(
    "data,frame,expected_payload",
    [
        pytest.param(
            *itemgetter("data", "frame", "expected_payload")(testcase),
            id=testcase["name"],
        )
        for testcase in TESTCASES
    ],
)
@pytest.mark.parametrize(
    "pre_filter_by_type",
    [False, True],
    ids=["non_pre_filtered", "pre_filtered"],
)
def test_can_project_data(
    data,
    frame,
    expected_payload,
    snapshot,
    request: pytest.FixtureRequest,
    pre_filter_by_type,
):
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

    frame = JsonLDFrame(frame)
    selected_fields = {"@type", *frame.get_fields()}
    vocabulary = Vocabulary(data)

    with (
        pytest.raises(expected_payload)
        if _test_should_fail(expected_payload)
        else nullcontext()
    ):
        framed = vocabulary.project(
            frame,
            callbacks=[lambda framed: select_fields(framed, selected_fields)],
            pre_filter_by_type=pre_filter_by_type,
        )
    if _test_should_fail(expected_payload):
        return
    graph = framed["@graph"]

    for item in graph:
        item_fields = set(item.keys())
        assert item_fields <= selected_fields, (
            f"Item fields {item_fields} are not a subset of selected fields {selected_fields}"
        )

    base = snapshot / "base"
    snapshot_file_name = request.node.callspec.id.replace(
        "non_pre_filtered-", ""
    ).replace("pre_filtered-", "")
    snapshot_path = base / f"{snapshot_file_name}.data.yaml"

    compare_data(snapshot_path, current_data=graph, update=True)


@pytest.mark.parametrize(
    "data,frame",
    [
        pytest.param(
            *itemgetter("data", "frame")(testcase),
            id=testcase["name"],
        )
        for testcase in TESTCASES
        if not _test_should_fail(testcase.get("expected_payload"))
    ],
)
def test_can_validate_data(data, frame):
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
    frame = JsonLDFrame(frame)
    selected_fields = {"@type", *frame.get_fields()}
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

    frame = JsonLDFrame.load(frame_path)

    selected_fields = {"@type", *frame.get_fields()}
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
