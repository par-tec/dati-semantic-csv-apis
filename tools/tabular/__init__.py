"""
This module supports the generation of tabular data representations
of RDF datasets expressed in JSON-LD format.

These datasets are expected to follow specific framing rules
and to be generated from projector.py.

Moreover this module provides utilities to create
a Data Package descriptor for the generated CSV files:
this data package is generated from the framed JSON-LD data.
"""

import csv
from collections.abc import Collection
from pathlib import Path

import pandas as pd
from frictionless import Package
from rdflib import Graph

from tools.base import TEXT_TURTLE
from tools.projector import JsonLD, JsonLDFrame
from tools.tabular.metadata import create_datapackage
from tools.utils import expand_context_to_absolute_uris
from tools.vocabulary import Vocabulary

IGNORE_RDF_PROPERTIES: Collection[str] = (
    "http://www.w3.org/2004/02/skos/core#inScheme",
    "http://www.w3.org/2004/02/skos/core#broader",
)

# TODO: define the CSV dialect using frictionless schema, and use it to create the CSV files.
# Another option is to use the frictionless datapackage to project the JSON-LD data into CSV directly.
# See https://frictionlessdata.io/docs/tabular-data-package/#csv-dialect
CSV_DIALECT = {
    "dialect": {
        # "csvddfVersion": "1.2",
        "delimiter": ",",
        "doubleQuote": True,
        "lineTerminator": "\r\n",
        "quoteChar": '"',
        "skipInitialSpace": True,
        "header": True,
        "commentChar": "#",
    }
}


class Tabular(Vocabulary):
    """
    This class provides utilities to create a tabular representation of RDF datasets
    following specific framing rules.

    This class loads some settings from
    a datapackage descriptor.
    """

    def __init__(
        self,
        rdf_data: str | Path,
        frame: JsonLDFrame,
        ignore_rdf_properties: Collection[str] = IGNORE_RDF_PROPERTIES,
        sort_by: tuple = ("id", "label"),
        format=TEXT_TURTLE,
    ):
        super().__init__(rdf_data, format=format)
        self.frame: JsonLDFrame = frame
        self.ignore_rdf_properties = ignore_rdf_properties
        self.sort_by = sort_by

        self.data: JsonLD = {}
        self.df: pd.DataFrame | None = None
        self._dialect: dict = CSV_DIALECT.copy()
        self._datapackage: dict | None = None

    @property
    def csv_dialect(self) -> dict:
        """
        Get the CSV dialect settings from the datapackage descriptor.

        Returns:
            dict: CSV dialect settings
        """
        return self._dialect

    def set_dialect(
        self,
        *,
        delimiter: str = ",",
        lineTerminator: str = "\r\n",
        quoteChar: str = '"',
        doubleQuote: bool = True,
        escapechar: str | None = None,
        skipInitialSpace: bool = False,
        header: bool = True,
        commentChar: str = "#",
    ):
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

        TODO: Process skipInitialSpace.
        """

        if escapechar:
            raise ValueError("Unsupported escapechar.")
        if header is not True:
            raise ValueError(
                f"Unsupported header '{header}' in CSV dialect. Only header: true is supported."
            )
        if commentChar != "#":
            raise ValueError(
                f"Unsupported commentChar '{commentChar}' in CSV dialect"
            )
        if doubleQuote is not True:
            raise ValueError(
                f"Unsupported doubleQuote '{doubleQuote}' in CSV dialect"
            )

        self._dialect = {
            "delimiter": delimiter,
            "lineTerminator": lineTerminator,
            "quoteChar": quoteChar,
            "doubleQuote": doubleQuote,
            "escapechar": escapechar,
            "skipInitialSpace": skipInitialSpace,
            "header": header,
            "commentChar": commentChar,
        }

    @property
    def datapackage(self) -> dict:
        """
        Get the datapackage descriptor for this tabular instance.

        Returns:
            dict: Frictionless datapackage descriptor
        """
        if not self._datapackage:
            self._datapackage = self.datapackage_stub()
        return self._datapackage

    @datapackage.setter
    def datapackage(self, datapackage: dict) -> None:
        """
        Set the datapackage descriptor for this tabular instance
        and validates its *syntax* but not its content.
        This will be used to configure
        the CSV output settings when calling to_csv().

        Args:
            datapackage (dict): Frictionless datapackage descriptor
        """
        if not Package(datapackage):
            raise ValueError(f"Invalid datapackage: {datapackage}")
        self._datapackage = datapackage

    def datapackage_stub(
        self,
        resource_path: Path | None = None,
    ) -> dict:
        """
        Create a frictionless datapackage stub descriptor
        from the metadata of the RDF graph.

        Parameters:
        - resource_path: Optional path to the CSV file resource.
        If provided, adds a data resource
        with information extracted from the RDF graph
        and the JSON-LD frame.

        Returns:
            dict: Frictionless datapackage descriptor stub.
        """
        metadata: Graph = self.metadata()
        _datapackage = create_datapackage(
            metadata, next(iter(metadata.subjects())), resources=[]
        )

        # If the package is not valid, __init__ will raise an error.
        # at this point we can't fully validate the package because
        # this is just a stub.
        package = Package(_datapackage)
        if not package:
            raise ValueError(f"Invalid datapackage: {_datapackage}")

        if resource_path:
            resource_name = (
                _datapackage.get("name", resource_path.stem)
                if _datapackage
                else resource_path.stem
            )
            _datapackage["resources"] = [
                self.dataresource_stub(resource_name, resource_path)
            ]
        return _datapackage

    def dataresource_stub(self, resource_name, resource_path) -> dict:
        """
        Create a frictionless data resource dictionary from JSON-LD data.
        See https://datapackage.org/standard/data-resource/

        The input information come from:

        - the JSON-LD frame that is used to project the data into tabular format,
        specifically every CSV field MUST match a property defined in the frame's @context,
        eventually mapped to `null` if not present in the original RDF graph;
        - the JSON Schema used to validate data syntax and types.

        Since CSV does not provide a means to define data types,
        you need a schema to correctly interpret its values.
        These data types are defined in the "schema" section of the data resource dictionary.
        and must be compatible with the JSON Schema used in the OAS and,
        when present, with the xsd:schema defined in the RDF vocabulary.

        After the dataresource is created,
        the CSV file is validated against its schema.

        Args:
            resource_path: Path to the CSV file resource
            frame: JSON-LD frame containing the @context with field mappings
            datapackage: Datapackage dictionary with metadata
        Returns:
            dict: Data resource dictionary

        """
        if not resource_path:
            raise ValueError("resource_path is required")

        if not self.frame or "@context" not in self.frame:
            raise ValueError("frame must contain @context")

        # Extract field definitions from frame's @context
        context = self.frame["@context"]
        expanded_context = expand_context_to_absolute_uris(context)
        fields = []

        for key, value in context.items():
            if value == "@id":
                fields.append({"name": key, "type": "string"})
                break

        for key, value in expanded_context.items():
            if key.startswith("@"):
                continue  # Skip JSON-LD keywords
            if isinstance(value, str):
                if value.endswith(("#", "/", ":")):
                    continue  # Skip namespace declarations
                if value in self.ignore_rdf_properties:
                    continue  # Skip ignored RDF properties

            # breakpoint()  # Debugging: check field extraction logic
            # Determine field type based on @type in context or use string as default
            field_type = "string"
            if isinstance(value, dict):
                xsd_type = value.get("@type", "")
                if "integer" in xsd_type or "int" in xsd_type:
                    field_type = "integer"
                elif "date" in xsd_type:
                    field_type = "date"
                elif "boolean" in xsd_type:
                    field_type = "boolean"
                elif "number" in xsd_type or "decimal" in xsd_type:
                    field_type = "number"

            # Special handling for common fields
            if key in ["id", "url"]:
                field_type = "string"
            elif key == "level":
                field_type = "integer"

            fields.append({"name": key, "type": field_type})

        return {
            # Constant values.
            "type": "table",
            "scheme": "file",
            "format": "csv",
            "mediatype": "text/csv",
            "encoding": "utf-8",
            # Dynamic values.
            "name": resource_name,
            "path": str(resource_path),
            "schema": {
                "fields": fields,
                "x-jsonld-context": context,
            },
            "dialect": self.csv_dialect,
        }

    def _pandas_csv_dialect(self):
        ret = {
            # Hardcoded settings, to ensure consistent CSV output.
            "quoting": csv.QUOTE_ALL,  # quote all fields
            "encoding": "utf-8",
            "escapechar": "\\",
            # Settings from datapackage descriptor.
            "sep": self._dialect["delimiter"],
            "lineterminator": self._dialect["lineTerminator"],
            "header": self._dialect["header"],
        }
        if self._dialect["quoteChar"] == '"':
            ret["doublequote"] = True
            ret["quotechar"] = '"'
        elif self._dialect["quoteChar"] == "'":
            ret["doublequote"] = False
            ret["quotechar"] = "'"
        else:
            raise ValueError(
                f"Unsupported quoteChar '{self._dialect['quoteChar']}' in CSV dialect"
            )
        return ret

    def load(self, data: JsonLD | None = None) -> pd.DataFrame:
        """
        Create a CSV from a JSON-LD document framed according
        to the provided JSON-LD frame.

        Args:
            data: Framed JSON-LD document to be loaded into a DataFrame.
                  XXX: If not provided, the method will attempt to project the data
                  using the provided JSON-LD frame.
            frame: JSON-LD frame used for framing the data
            ignore_rdf_properties: Collection of RDF properties to ignore in the CSV output. By default, includes "skos:inScheme" and "skos:broader".

        Returns:
            pd.DataFrame: CSV representation of the framed data.

        """
        self.data = data if data is not None else self.data
        # XXX: Consider avoiding projecting data here.
        if not self.data:
            self.data = self.project(self.frame)
        if not self.data:
            raise ValueError("No data to load.")
        items = self.data.get("@graph")
        if not items:
            raise ValueError("Framed data must contain a @graph.")
        # The generated CSV has the following requirements:
        # - columns must not reference JSON-LD keywords (e.g., @id, @type)
        # - string columns must always be quoted, and the content
        #   must be escaped properly
        self.df = pd.DataFrame(items)

        return self.df

    def to_csv(self, output_path: str, **kwargs):
        """
        Write the CSV representation of the framed data to a file,
        using the information provided by the datapackage descriptor.

        To invoke this method, a datapackage MUST be created first,
        because the metadata MUST already exist.
        """
        if not self._datapackage:
            raise ValueError(
                "Datapackage descriptor is required to configure CSV output settings."
                " Please set datapackage() before calling to_csv()."
            )
        if self.df is None:
            raise ValueError(
                "DataFrame is not loaded. Please call load() before to_csv()."
            )
        selected_columns = [
            field["name"]
            for field in self._datapackage.get("resources", [{}])[0]
            .get("schema", {})
            .get("fields", [])
        ]
        # Remove:
        # - JSON-LD keyword columns (those starting with @)
        # - the field associated with "skos:inScheme" must be dropped.
        self.df = self.df[selected_columns]
        # Sort:
        # - data must be sorted by the "id" column if present
        if "id" in self.df.columns:
            self.df.sort_values(by=["id"], ignore_index=True, inplace=True)
        self.df.to_csv(
            output_path,
            index=False,
            **self._pandas_csv_dialect(),
            **kwargs,
        )
