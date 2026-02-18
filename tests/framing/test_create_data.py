from operator import itemgetter
from pathlib import Path

import pytest
import yaml

from tests.from_samples import frame_context_fields
from tools.projector import JsonLD, framer

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
def test_can_frame_data(data, frame, expected_payload):
    """
    Given:
    - A framing context
    - An RDF graph

    When:
    - I create a framed API from the RDF graph and the framing context

    Then:
    - I expect the framed API to only include fields from the framing context, or "@type"
    """
    framed: JsonLD = framer(frame, data)
    _, graph = framed["@context"], framed["@graph"]
    frame_fields = frame_context_fields(frame) + ["@type"]
    for item in graph:
        # Check that only fields in frame context are present
        item_fields = list(item.keys())
        for f in item_fields:
            if f not in frame_fields:
                item_fields.remove(f)
        for f in item_fields:
            assert f in frame_fields, f"Field {f} not in frame context fields"
    assert graph == expected_payload, "Framed data does not match expected payload"


@pytest.mark.parametrize(
    "vocabulary_ttl",
    vocabularies,
    ids=[x.name for x in vocabularies],
)
def test_generate_api_data(vocabulary_ttl):
    """
    Given:
    - A controlled vocabulary RDF graph
    - A framing context that selects preferred terms

    When:
    - I create a framed API from the RDF graph and the framing context

    Then:
    - I expect the framed API to only include preferred terms
    """
    data = vocabulary_ttl.read_text()
    frame_path = vocabulary_ttl.with_suffix(".frame.yamlld")
    if not frame_path.exists():
        pytest.skip(f"No framing context found for {vocabulary_ttl}")
    frame = yaml.safe_load(frame_path.read_text())
    data_ttl = vocabulary_ttl.read_text()

    framed = framer(frame, data_ttl)
    _, graph = framed["@context"], framed["@graph"]

    filtered_items = framed["statistics"]["filtered"]
    for id_ in [x["url"] for x in graph]:
        if id_ in filtered_items:
            filtered_items.remove(id_)

    frame_fields = frame_context_fields(frame) + ["@type"]
    for item in graph:
        # Check that only fields in frame context are present
        item_fields = list(item.keys())
        for f in item_fields:
            if f not in frame_fields:
                item_fields.remove(f)
        for f in item_fields:
            assert f in frame_fields, f"Field {f} not in frame context fields"

    data = vocabulary_ttl.with_suffix(".data.yaml")
    data.write_text(yaml.safe_dump(framed))
