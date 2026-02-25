"""
Validate tabular data and metadata reading from a frictionless datapackage.
"""

import json
from pathlib import Path

from frictionless import Package
from rdflib.compare import IsomorphicGraph

from tools.base import APPLICATION_LD_JSON, JsonLD
from tools.utils import IGraph


class TabularValidator:
    def __init__(self, datapackage: dict, basepath: Path):
        self.datapackage = datapackage
        self.basepath = basepath
        self.package: Package | None = None

    def load(self):
        """
        Load the datapackage and validate its structure.

        All functions in this class assume that the datapackage has already been loaded and validated.
        """
        package = Package(self.datapackage, basepath=self.basepath)
        validation_result = package.validate()
        for task in validation_result.tasks:
            if task.errors:
                raise ValueError(
                    f"Validation errors in resource '{task.resource.name}': {task.errors}"
                )
        self.package = package
        self._context = self._load_jsonld_context()
        self.csv_graph = None

    @property
    def context(self) -> dict:
        """Return the JSON-LD context extracted from the datapackage descriptor."""
        if not self._context:
            raise ValueError(
                "Run 'load()' to load and validate the datapackage before accessing the JSON-LD context."
            )
        return self._context

    def _load_jsonld_context(self) -> dict:
        """Validate the presence of a JSON-LD context in the datapackage descriptor."""
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
            context = schema.get("x-jsonld-context", None)
            if context is None:
                raise ValueError(
                    f"Resource '{resource.name}' must contain an 'x-jsonld-context' in its schema."
                )

            if not isinstance(context, dict):
                raise ValueError(
                    f"The 'x-jsonld-context' in resource '{resource.name}' must be a JSON object."
                )

        return context

    def to_jsonld(self) -> JsonLD:
        """Validate the datapackage descriptor and resources."""
        resource = next(iter(self.package.resources))
        rows = resource.read_rows()
        return {
            "@context": self._context,
            "@graph": [x.to_dict() for x in rows],
        }

    def to_graph(self) -> IsomorphicGraph:
        """Convert the JSON-LD representation of the tabular data to an RDF graph."""
        if not self.csv_graph:
            self.csv_graph: IsomorphicGraph = IGraph.parse(
                data=json.dumps(self.to_jsonld()),
                format=APPLICATION_LD_JSON,
            )
        return self.csv_graph

    def validate(self, original_graph: IsomorphicGraph, min_triples: int = 1):
        """Validate that the RDF graph derived from the CSV data is a subset of the original RDF graph."""
        csv_graph: IsomorphicGraph = self.to_graph()
        if len(csv_graph) < min_triples:
            raise ValueError(
                f"CSV-derived RDF graph has {len(csv_graph)} triples, which is less than the minimum expected {min_triples} triples."
            )
        extra_triples = csv_graph - original_graph
        if len(extra_triples) > 0:
            raise ValueError(
                f"CSV-derived RDF graph contains {len(extra_triples)} triples not present in original RDF graph"
            )
