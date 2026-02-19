import json
import logging
import time
from collections.abc import Callable, Iterable
from itertools import batched
from pathlib import Path
from typing import TypedDict

from pyld import jsonld
from rdflib import Graph

log = logging.getLogger(__name__)


JsonLD = TypedDict("JsonLD", {"@context": dict, "@graph": list}, total=False)
JsonLDFrame = TypedDict("JsonLDFrame", {"@context": dict}, total=False)


def to_jsonld(rdf_data: str) -> JsonLD:
    """
    Convert RDF data in Turtle format to JSON-LD.

    Args:
        rdf_data: RDF data in Turtle format
    Returns:
        JsonLD: JSON-LD representation of the RDF data
    """
    g = Graph()
    g.parse(data=rdf_data, format="text/turtle")
    ld = g.serialize(format="application/ld+json")
    ld_doc: JsonLD = json.loads(ld)
    return ld_doc


def framer(frame: JsonLDFrame, rdf_data: str, batch_size: int = 0) -> JsonLD:
    """
    Apply a JSON-LD frame to a JSON-LD serialized RDF data to produce a JSON output.
    When requested, it processes in batches to improve performance:
    this can be useful for large datasets,
    but may cause issues with nested entries
    that span across batches because properties
    that are not included in the batch may not be embedded properly.

    Args:
        frame: JSON-LD frame specification
        rdf_data: RDF data in Turtle format
        batch_size: Number of records to process per batch.
            If 0 (default), process all at once to ensure
            proper embedding of referenced properties.

    Returns:
        JsonLD: Framed JSON-LD document containing @context and @graph fields.
    """

    ld_doc: JsonLD = to_jsonld(rdf_data)
    original_context = frame.get("@context", {})

    # Determine items to process
    if isinstance(ld_doc, dict) and "@graph" in ld_doc:
        items = ld_doc["@graph"]
    elif isinstance(ld_doc, list):
        items = ld_doc
    else:
        items = [ld_doc]

    num_items = len(items)
    log.info(
        f"Dataset contains {num_items} items, processing "
        + (f"in batches of {batch_size}" if batch_size > 0 else "without batching")
    )

    # Always use batch processing for consistent code path
    all_framed_items: list = []
    statistics: dict[str, int | list] = {
        "source_items": 0,
        "framed_items": 0,
        "filtered": [],
    }

    #
    # To reduce issues with large datasets (e.g., RAM usage, ...)
    # process items in batches.
    # Note: when "@embed" != "@never", nested entries may not
    #   be fully captured if they span across batches.
    #
    for batch in batched(items, batch_size) if batch_size > 0 else [items]:
        batch_len: int = len(batch)
        log.info(f"Processing batch ({batch_len} items)")
        statistics["source_items"] += batch_len  # type: ignore

        # Create batch document with original context
        batch_doc: JsonLD = {"@context": original_context, "@graph": list(batch)}

        batch_frame_start = time.time()
        framed_batch = jsonld.frame(
            batch_doc, frame, options={"processingMode": "json-ld-1.1"}
        )
        batch_frame_time = time.time() - batch_frame_start
        log.info(f"Batch framing took {batch_frame_time:.3f}s")

        #
        # Control block for debugging framing issues.
        #
        assert "@graph" in framed_batch

        typed_urls = [
            i
            for i in framed_batch["@graph"]
            for v in i.get("vocab", [])
            if v and v.get("@type")
        ]
        assert not typed_urls
        #
        # Log differences to troubleshoot
        #   the framing process.
        #
        framed_items_len = len(framed_batch["@graph"])
        batch_ids = {i["@id"].split("/")[-1] for i in batch}
        framed_ids = {Path(i["url"]).name for i in framed_batch["@graph"]}

        if framed_items_len != batch_len:
            statistics["filtered"].extend(list(batch_ids - framed_ids))  # type: ignore
            # breakpoint()

        # Extract framed items from batch
        all_framed_items.extend(framed_batch["@graph"])

    statistics["framed_items"] = len(all_framed_items)

    # Assemble final result
    framed: JsonLD = {"@context": frame.get("@context", {}), "@graph": all_framed_items}
    framed["statistics"] = statistics  # type: ignore

    log.info(f"Batched framing completed, total items: {len(all_framed_items)}")

    return framed


def update_frame_with_key_field(framed: dict, base_uri: str) -> None:
    """
    If the "url" field of every entry starts with base_uri,
    we can safely assume that the relative part of the URI
    can be used as a "key" field.
    So, add the "key" field to every entry containing the relative part of the URI.

    Since a JSON-LD context can only define one "@id" mapping,
    and this is "uri",
    disassociate the "key" field in the "@context".
    """
    URI = "url"
    base_uri_len = len(base_uri)
    context, graph = framed["@context"], framed["@graph"]
    # Disassociate "key" field in context.
    context["key"] = None

    for entry in graph:
        if not entry[URI].startswith(base_uri):
            raise ValueError(
                f"Entry URI {entry[URI]} does not start with base URI {base_uri}"
            )
        entry["key"] = entry[URI][base_uri_len:]


def select_fields(framed: JsonLD, selected_fields: list[str]) -> None:
    """
    Slice the give data retaining only the
    fields explicitly mentioned in the frame,
    and discarding the others, (e.g., the remnants
    of an rdf:Property that have an unmentioned
    `@language` or `@type` field).
    """
    _, graph = framed["@context"], framed["@graph"]
    for item in graph:
        item_fields = list(item.keys())
        for f in item_fields:
            if f not in selected_fields:
                del item[f]


def project(
    frame: JsonLDFrame,
    rdf_data: str,
    batch_size: int = 0,
    callbacks: Iterable[Callable] = (),
) -> JsonLD:
    """
    Apply the frame to the RDF data and then project the result to only include fields in the frame context.

    Args:
        frame: JSON-LD frame specification
        rdf_data: RDF data in Turtle format
        batch_size: Number of records to process per batch. If 0, process all at once.
        callbacks: Optional list of callback functions to call after processing each batch.
    Returns:
        JsonLD: Projected JSON-LD document containing only fields in the frame context.
    """
    framed = framer(frame, rdf_data, batch_size)

    for callback in callbacks or []:
        callback(framed)

    return framed


def frame_context_fields(frame) -> list:
    """
    Extract field names from a JSON-LD frame,

    Including:
    - '@context' fields
    - '@default' fields
    - detached fields (i.e., fields with value `null` in the frame).

    Excluding:
    - Namespace declarations (i.e., fields whose value is a URI string)
    - `@-`prefixed JSON-LD keywords (e.g., `@id`, `@type`, etc.)
    """

    def is_field(k, v):
        if k.startswith("@"):
            return False
        if isinstance(v, str) and v.startswith("http"):
            return False
        return True

    context_fields = [k for k, v in frame.get("@context", {}).items() if is_field(k, v)]

    default_fields = [
        k for k, v in frame.items() if isinstance(v, dict) and "@default" in v
    ]

    detached_fields = [k for k, v in frame.items() if isinstance(v, dict) and v is None]

    return list(set(context_fields + default_fields + detached_fields))
