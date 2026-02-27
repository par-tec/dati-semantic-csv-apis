"""
Validate tabular data and metadata reading from a frictionless datapackage.
"""

import json
import logging
from pathlib import Path

from frictionless import Package, Resource
from rdflib.compare import IsomorphicGraph

from tools.base import APPLICATION_LD_JSON, JsonLD
from tools.utils import IGraph

log = logging.getLogger(__name__)


class TabularValidator:
    def __init__(self, datapackage: dict, basepath: Path):
        self.datapackage = datapackage
        self.basepath = basepath
        self.package: Package = Package(
            self.datapackage, basepath=str(self.basepath)
        )
        self.csv_graph: IsomorphicGraph | None = None
        self.stats: dict = {
            "csv_triples": -1,
            "original_triples": -1,
            "extra_triples": -1,
            "csv_rows": -1,
        }

    def load(self):
        """
        Load the datapackage and validate its structure.

        All functions in this class assume that the datapackage has already been loaded and validated.
        """
        log.debug("Validating datapackage structure...")
        validation_result = self.package.validate()
        for task in validation_result.tasks:
            if task.errors:
                raise ValueError(
                    f"Validation errors in resource '{task.name}': {task.errors}"
                )
        log.debug("Datapackage structure is valid.")
        self._load_jsonld_context()

    @property
    def context(self) -> dict:
        """Return the JSON-LD context extracted from the datapackage descriptor."""
        if not self._context:
            raise ValueError(
                "Run 'load()' to load and validate the datapackage before accessing the JSON-LD context."
            )
        return self._context

    def _load_jsonld_context(self) -> None:
        """
        Validate the presence of a JSON-LD context in the datapackage descriptor
        and load it.
        """
        log.debug("Extracting JSON-LD context from datapackage...")
        if not self.package:
            raise ValueError(
                "Run 'load()' to load and validate the datapackage before accessing the JSON-LD context."
            )

        if not self.package.resources:
            raise ValueError("Datapackage must contain a 'resources' field.")
        for i, resource in enumerate(self.package.resources):
            if i > 0:
                raise ValueError("Datapackage must contain only one resource.")
            if not resource.schema or not resource.schema.fields:
                raise ValueError(
                    f"Resource '{resource.name}' must contain a schema with fields."
                )
            schema = resource.schema.to_dict()
            context: dict | None = schema.get("x-jsonld-context", None)
            if context is None:
                raise ValueError(
                    f"Resource '{resource.name}' must contain an 'x-jsonld-context' in its schema."
                )

            if not isinstance(context, dict):
                raise ValueError(
                    f"The 'x-jsonld-context' in resource '{resource.name}' must be a JSON object."
                )
            self._context = context
            log.debug(f"JSON-LD context extracted: {self._context}")

    def to_jsonld(self) -> JsonLD:
        """Validate the datapackage descriptor and resources."""
        resource: Resource = next(iter(self.package.resources))
        rows = resource.read_rows()
        self.stats["csv_rows"] = len(rows)
        ret: JsonLD = {
            "@context": self._context,
            "@graph": [x.to_dict() for x in rows],
        }
        return ret

    def to_graph(self) -> IsomorphicGraph:
        """Convert the JSON-LD representation of the tabular data to an RDF graph."""
        if self.csv_graph is None:
            self.csv_graph = IGraph.parse(
                data=json.dumps(self.to_jsonld()),
                format=APPLICATION_LD_JSON,
            )
        return self.csv_graph

    def validate(
        self, original_graph: IsomorphicGraph, min_triples: int = 1
    ) -> dict:
        """Validate that the RDF graph derived from the CSV data is a subset of the original RDF graph."""
        csv_graph: IsomorphicGraph = self.to_graph()
        csv_triples: int = len(csv_graph)
        if csv_triples < min_triples:
            raise ValueError(
                f"CSV-derived RDF graph has {csv_triples} triples,"
                f" which is less than the minimum expected {min_triples} triples."
            )
        log.info(
            f"CSV-derived RDF graph has {csv_triples} triples, which meets the minimum expected {min_triples} triples."
        )
        extra_triples = csv_graph - original_graph
        if len(extra_triples) > 0:
            raise ValueError(
                f"CSV-derived RDF graph contains {len(extra_triples)} triples not present in original RDF graph"
            )
        self.stats.update(
            {
                "csv_triples": csv_triples,
                "original_triples": len(original_graph),
                "extra_triples": len(extra_triples),
            }
        )
        return self.stats
