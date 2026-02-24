from pathlib import Path

import yaml
from jsonschema import validate
from rdflib import DCAT, DCTERMS, OWL, SKOS, Graph, Namespace, URIRef

from tools.projector import JsonLDFrame

# Define namespaces
NDC = Namespace("https://w3id.org/italia/onto/NDC/")
DATADIR = Path(__file__).parent.parent / "data"

DATAPACKAGE_SCHEMA_YAML = DATADIR / "datapackage.schema.json"
DATAPACKAGE_SCHEMA = yaml.safe_load(DATAPACKAGE_SCHEMA_YAML.read_text())


def create_dataresource(
    resource_path: Path, frame: JsonLDFrame, datapackage: dict
):
    """
    Create a frictionless data resource dictionary from JSON-LD RDF data.
    The input information come from:

    - the RDF vocabulary data (or the information extracted via create_datapackage);
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

    See https://datapackage.org/standard/data-resource/

    Args:
        resource_path: Path to the CSV file resource
        frame: JSON-LD frame containing the @context with field mappings
        datapackage: Datapackage dictionary with metadata
    Returns:
        dict: Data resource dictionary
    """
    if not resource_path:
        raise ValueError("resource_path is required")

    if not frame or "@context" not in frame:
        raise ValueError("frame must contain @context")

    # Extract field definitions from frame's @context
    context = frame["@context"]
    fields = []

    for key, value in context.items():
        # Skip namespace declarations (they're URIs)
        if isinstance(value, str) and (
            value.startswith("http://") or value.startswith("https://")
        ):
            continue

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

    # Get resource name from path or datapackage
    resource_name = (
        datapackage.get("name", resource_path.stem)
        if datapackage
        else resource_path.stem
    )

    return {
        "name": resource_name,
        "type": "table",
        "path": str(resource_path),
        "scheme": "file",
        "format": "csv",
        "mediatype": "text/csv",
        "encoding": "utf-8",
        "schema": {"fields": fields},
    }


def create_datapackage(
    vocabulary: Graph,
    vocabulary_uri: URIRef,
    resources: list,
) -> dict:
    """
    Create a frictionless datapackage from JSON-LD RDF data.

    Args:
        vocabulary: RDF graph containing the data
        vocabulary_uri: URI of the vocabulary (concept scheme) to extract metadata for
        resources: List of data resources to include in the datapackage
            (e.g., from a CSV file)
            by default, uses SKOS vocabulary terms, otherwise use others (e.g., DCTERMS, DCAT, OWL)
    Returns:
        dict: Frictionless datapackage dictionary
    """

    if not vocabulary:
        raise ValueError(f"No triples found for {vocabulary_uri} in RDF data")

    conformsTo = vocabulary.value(vocabulary_uri, DCTERMS.conformsTo)
    language = vocabulary.value(vocabulary_uri, DCTERMS.language)
    if str(language).lower().endswith(("/it", "/ita")):
        lang = "it"
    elif str(language).lower().endswith(("/en", "/eng")):
        lang = "en"
    else:
        raise NotImplementedError(
            f"Unsupported language '{language}' for vocabulary {vocabulary_uri}"
        )
        lang = None

    # Check if vocabulary conforms to any ofdswith

    def get_identifier(predicate, unique=True, required=True):
        values = set(
            str(obj) for obj in vocabulary.objects(vocabulary_uri, predicate)
        )
        if unique and len(values) > 1:
            raise ValueError(
                f"Expected exactly one value for {predicate}, found {len(values)}: {values}"
            )
        # If the identifier has a language-tagged literal,
        #  raise an error.
        if any(
            hasattr(obj, "language") and obj.language
            for obj in vocabulary.objects(vocabulary_uri, predicate)
        ):
            raise ValueError(
                f"Expected a non-language-tagged literal for {predicate}, but found language-tagged literals: {values}"
            )
        if required and not values:
            raise ValueError(
                f"Expected a value for {predicate}, but found none"
            )
        return next(iter(values)) if values else None

    # Helper function to get literal value
    def get_value(predicate, lang=None):
        for obj in vocabulary.objects(vocabulary_uri, predicate):
            if lang and hasattr(obj, "language") and obj.language != lang:
                continue
            return str(obj)
        return None

    # Helper function to get all values as list
    def get_values(predicate, lang=None):
        values = []
        for obj in vocabulary.objects(vocabulary_uri, predicate):
            if lang and hasattr(obj, "language") and obj.language != lang:
                continue
            values.append(str(obj))
        return values if values else None

    def get_first_value(predicates, lang=None):
        for predicate in predicates:
            value = get_value(predicate, lang=lang)
            if value:
                return value
        return None

    # Map RDF properties to Frictionless datapackage fields
    datapackage = {
        "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
        "name": get_value(NDC.keyConcept) or "",
        "id": get_identifier(DCTERMS.identifier, unique=True, required=False)
        or str(vocabulary_uri),
        "title": get_first_value([DCTERMS.title, SKOS.prefLabel], lang=lang)
        or "",
        "resources": resources or [],
    }

    # Add optional fields if present
    version = get_value(OWL.versionInfo)
    if version:
        datapackage["version"] = version

    description = get_first_value(
        [DCTERMS.description, SKOS.definition], lang=lang
    )
    if description:
        datapackage["description"] = description

    homepage = get_value(DCAT.accessURL)
    if homepage:
        datapackage["homepage"] = homepage

    created = get_value(DCTERMS.issued)
    if created:
        datapackage["created"] = created

    keywords = get_values(DCAT.keyword)
    if keywords:
        keywords.sort()
        datapackage["keywords"] = keywords

    licenses = get_values(DCTERMS.license)
    if licenses:
        datapackage["licenses"] = licenses

    # validate_datapackage(datapackage)
    return datapackage


def validate_datapackage(datapackage: dict | Path) -> None:
    """Validate a datapackage dictionary against the frictionless datapackage JSON Schema."""

    datapackage_dict = (
        yaml.safe_load(datapackage.read_text())
        if isinstance(datapackage, Path)
        else datapackage
    )
    validate(datapackage_dict, DATAPACKAGE_SCHEMA)
