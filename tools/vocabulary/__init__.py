import json
import logging
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import cast

from rdflib import Graph

from tools.base import APPLICATION_LD_JSON, TEXT_TURTLE, JsonLD, JsonLDFrame
from tools.projector import framer

log = logging.getLogger(__name__)


class Vocabulary:
    """
    This class represents a vocabulary,
    that can be loaded, serialized, and projected
    in different formats.

    A vocabulary is defined by a graph.

    Functions supports both loading from a stream or a file.

    By default, uses Oxigraph.
    """

    def __init__(self, rdf_data: str | Path, format=TEXT_TURTLE):
        self.graph = Graph()
        ts: float = time.time()
        if isinstance(rdf_data, Path):
            self.graph.parse(rdf_data, format=format)
        else:
            self.graph.parse(data=rdf_data, format=format)
        log.debug(
            f"Parsed {len(self.graph)} RDF triples in {time.time() - ts:.3f}s"
        )

        self._uri: str | None = None
        self._metadata = None

    def serialize(self, format=APPLICATION_LD_JSON) -> str:
        ts: float = time.time()
        serialized: str = self.graph.serialize(format=format)
        log.debug(f"Serialized RDF to {format} in {time.time() - ts:.3f}s")
        return serialized

    def json_ld(self) -> JsonLD:
        """
        Convert RDF data in Turtle format to JSON-LD.

        Args:
            rdf_data: RDF data in Turtle format
        Returns:
            JsonLD: JSON-LD representation of the RDF data
        """
        data = json.loads(self.serialize(format=APPLICATION_LD_JSON))
        if isinstance(data, dict):
            if "@graph" not in data:
                raise ValueError(
                    "Expected JSON-LD serialization to contain a top-level '@graph' key"
                )
            return cast(JsonLD, data)
        if isinstance(data, list):
            return cast(JsonLD, {"@graph": data})
        raise ValueError("Expected JSON-LD serialization to be a JSON object")

    def metadata(self) -> Graph:
        """
        Extract a subgraph representing a vocabulary (concept scheme) from the RDF graph.

        Args:
            uri: URI of the vocabulary (concept scheme) to extract
            key_concept: Optional URI of the key concept to filter by
        Returns:
            Graph: RDF graph representing the extracted vocabulary
        """
        query = """
            PREFIX NDC: <https://w3id.org/italia/onto/NDC/>

            CONSTRUCT {
                ?vocab ?p ?o .
                ?vocab NDC:keyConcept ?keyConcept .
            }
            WHERE {
                ?vocab
                    NDC:keyConcept ?keyConcept ;
                    ?p ?o .
            }
        """
        res = self.graph.query(query)
        _metadata: Graph = res.graph

        _metadata_uri = set(_metadata.subjects())
        do_i_have_just_one_vocab = len(_metadata_uri)
        if do_i_have_just_one_vocab != 1:
            raise ValueError(
                "Expected exactly one vocabulary in the RDF data",
                do_i_have_just_one_vocab,
            )

        return _metadata

    def uri(self) -> str:
        """
        Get the URI of the vocabulary (concept scheme) represented by the RDF graph.

        Returns:
            str: URI of the vocabulary
        """
        if not self._uri:
            metadata = self.metadata()
            vocab_uri = next(iter(metadata.subjects()))
            self._uri = str(vocab_uri)
        return self._uri

    def project(
        self,
        frame: JsonLDFrame,
        batch_size: int = 0,
        callbacks: Iterable[Callable] = (),
    ) -> JsonLD:
        """
        Apply the frame to the RDF data and then project the result to only include fields in the frame context.

        Args:
            frame: JSON-LD frame specification
            batch_size: Number of records to process per batch. If 0, process all at once.
            callbacks: Optional list of callback functions to call after processing each batch.
        Returns:
            JsonLD: Projected JSON-LD document containing only fields in the frame context.
        """
        ld_doc: JsonLD = self.json_ld()
        framed = framer(ld_doc, frame, batch_size)

        for callback in callbacks or []:
            log.debug(f"Applying callbacks to framed data: {callback.__name__}")
            callback(framed)
            log.info(f"Callback applied successfully: {callback.__name__}")
        return framed
