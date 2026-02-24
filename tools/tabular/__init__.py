"""
This module supports the generation of tabular data representations
of RDF datasets expressed in JSON-LD format.

These datasets are expected to follow specific framing rules
and to be generated from projector.py.

Moreover this module provides utilities to create
a Data Package descriptor for the generated CSV files:
this data package is generated from the framed JSON-LD data.
"""

from collections.abc import Collection
from pathlib import Path

import pandas as pd
from rdflib import Graph

import tools.utils
from tools.projector import JsonLD, JsonLDFrame
from tools.tabular.metadata import create_datapackage

IGNORE_RDF_PROPERTIES: Collection[str] = (
    "http://www.w3.org/2004/02/skos/core#inScheme",
    "http://www.w3.org/2004/02/skos/core#broader",
)

# TODO: define the CSV dialect using frictionless schema, and use it to create the CSV files.
# Another option is to use the frictionless datapackage to project the JSON-LD data into CSV directly.
# See https://frictionlessdata.io/docs/tabular-data-package/#csv-dialect
CSV_DIALECT = {
    "dialect": {
        "csvddfVersion": 1.2,
        "delimiter": ";",
        "doubleQuote": True,
        "lineTerminator": "\r\n",
        "quoteChar": '"',
        "skipInitialSpace": True,
        "header": True,
        "commentChar": "#",
    }
}


class Tabular:
    """
    This class provides utilities to create a tabular representation of RDF datasets
    expressed in JSON-LD format, following specific framing rules.

    This class loads some settings from
    a datapackage descriptor.
    """

    def __init__(
        self,
        data: JsonLD,
        frame: JsonLDFrame,
        ignore_rdf_properties: Collection[str] = IGNORE_RDF_PROPERTIES,
        sort_by: tuple = ("id", "label"),
    ):
        self.data: JsonLD = data
        self.frame: JsonLDFrame = frame
        self.ignore_rdf_properties = ignore_rdf_properties
        self.sort_by = sort_by

        self.df: pd.DataFrame | None = None

    def metadata(
        self, rdf_data: str | Path, vocabulary_uri: str, format="text/turtle"
    ) -> dict:
        """
        Extract metadata from RDF data and create a frictionless datapackage descriptor.

        Args:
            rdf_data: RDF data or pathlikes
            vocabulary_uri: URI of the vocabulary (concept scheme) to extract metadata for
        Returns:
            dict: Frictionless datapackage descriptor
        """
        if isinstance(rdf_data, Path):
            kwargs = {"source": rdf_data, "format": format}
        elif isinstance(rdf_data, str):
            kwargs = {"data": rdf_data, "format": format}
        else:
            raise ValueError("rdf_data must be a string or a Path")

        self.g: tools.utils.IsomorphicGraph = tools.utils.IGraph.parse(**kwargs)

        res = self.g.query("""
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
                     """)
        vocab: Graph = res.graph
        self.vocab = vocab
        vocabularies = set(vocab.subjects())
        do_i_have_just_one_vocab = len(vocabularies)
        if do_i_have_just_one_vocab != 1:
            raise ValueError(
                "Expected exactly one vocabulary in the RDF data",
                do_i_have_just_one_vocab,
            )

        datapackage = create_datapackage(
            vocab, next(iter(vocabularies)), resources=[]
        )
        return datapackage

    def set_dialect(self, dialect: dict):
        """
        Saves the CSV dialect settings taken from the datapackage descriptor
        and uses them to configure the CSV output.

        dialect:
            lineTerminator: "\n"
            quoteChar: '"'
            doubleQuote: true
            skipInitialSpace: false
            header: true

        sep=",",
        quoting=1,  # csv.QUOTE_ALL - quote all fields
        escapechar="\\",
        doublequote=True,
        encoding="utf-8",
        """

    def load(self):
        """
        Create a CSV from a JSON-LD document framed according
        to the provided JSON-LD frame.

        Args:
            data: Framed JSON-LD document
            frame: JSON-LD frame used for framing the data
            ignore_rdf_properties: Collection of RDF properties to ignore in the CSV output. By default, includes "skos:inScheme" and "skos:broader".

        Returns:
            pd.DataFrame: CSV representation of the framed data.

        """
        # Identify from the frame @context, the fields
        #   associated with the skos:inScheme property.
        context = self.frame["@context"]
        expanded_context = tools.utils.expand_context_to_absolute_uris(context)

        is_select_column = [
            lambda col: not col.startswith("@"),
            lambda col: (
                expanded_context.get(col) not in self.ignore_rdf_properties
            ),
        ]

        # Convert framed data to tabular format
        # tabular_data = tabularize(data)

        # The generated CSV has the following requirements:
        # - columns must not reference JSON-LD keywords (e.g., @id, @type)
        # - string columns must always be quoted, and the content
        #   must be escaped properly
        self.df = pd.DataFrame(self.data["@graph"])

        # Remove:
        # - JSON-LD keyword columns (those starting with @)
        # - the field associated with "skos:inScheme" must be dropped.
        self.df = self.df[
            [
                col
                for col in self.df.columns
                if all(predicate(col) for predicate in is_select_column)
            ]
        ]

        # Sort:
        # - data must be sorted by the "id" column if present
        if "id" in self.df.columns:
            self.df.sort_values(by=["id"], ignore_index=True, inplace=True)
        return self.df

    def to_csv(self, output_path: str, **kwargs):
        self.df.to_csv(
            output_path,
            sep=",",
            index=False,
            quoting=1,  # csv.QUOTE_ALL - quote all fields
            escapechar="\\",
            doublequote=True,
            encoding="utf-8",
        )
