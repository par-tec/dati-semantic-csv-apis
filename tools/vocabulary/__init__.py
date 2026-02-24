import json
import logging
import time
from pathlib import Path
from typing import TypedDict

from rdflib import Graph

TEXT_TURTLE = "text/turtle"
OX_TURTLE = "ox-turtle"
APPLICATION_LD_JSON = "application/ld+json"
log = logging.getLogger(__name__)
JsonLD = TypedDict("JsonLD", {"@context": dict, "@graph": list}, total=False)
JsonLDFrame = TypedDict("JsonLDFrame", {"@context": dict}, total=False)


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
            self.graph.parse(rdf_data, format=TEXT_TURTLE)
        else:
            self.graph.parse(data=rdf_data, format=TEXT_TURTLE)
        log.debug(
            f"Parsed RDF data in {time.time() - ts:.3f}s, graph has {len(self.graph)} triples"
        )

    def serialize(self, format=APPLICATION_LD_JSON) -> str:
        ts: float = time.time()
        serialized = self.graph.serialize(format=format)
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
        return json.loads(self.serialize(format=APPLICATION_LD_JSON))
