import json
import logging
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import frozendict
from jsonschema import ValidationError, validate
from rdflib import DCTERMS
from rdflib.plugins.parsers.jsonld import to_rdf

from tools.base import (
    APPLICATION_LD_JSON,
    APPLICATION_LD_JSON_FRAMED,
    DATADIR,
    TEXT_TURTLE,
    JsonLD,
    JsonLDFrame,
    JsonLDFunction,
    JSONLDText,
    RDFText,
)
from tools.vocabulary import LANG_NONE, Vocabulary, VocabularyMetadata

from .jsonschema import OAS3SchemaBuilder

log = logging.getLogger(__name__)

type OpenAPI = dict[str, Any]
OPENAPI_30_SCHEMA_JSON = DATADIR / "openapi_30.schema.json"
OAS30_SCHEMA = json.loads(OPENAPI_30_SCHEMA_JSON.read_text())
URI = "url"
EmptyOpenAPI: OpenAPI = frozendict.frozendict()


def _remove_jsonld_keys(obj: Any) -> Any:
    """Return a deep copy of `obj` without keys starting with '@'.

    TODO: this is used by Tabular and Apiable: move to a common utils module.
    """
    if isinstance(obj, dict):
        return {
            k: _remove_jsonld_keys(v)
            for k, v in obj.items()
            if not k.startswith("@")
        }
    if isinstance(obj, list):
        return [_remove_jsonld_keys(item) for item in obj]
    return obj


class Apiable(Vocabulary):
    """
    A Vocabulary that can be framed and projected as API data.

    This class extends Vocabulary with API-specific functionality,
    such as framing RDF data according to a JSON-LD frame and
    generating an OpenAPI schema from the framed data.

    The design is intentionally strict, trying to be
    as deterministic as possible even for dataset created
    by different organizations.
    """

    def __init__(
        self,
        rdf_data: RDFText | JSONLDText | JsonLD | Path,
        frame: JsonLDFrame,
        format=TEXT_TURTLE,
    ):
        if isinstance(rdf_data, (str, Path)):
            super().__init__(rdf_data, format=format)
        elif isinstance(rdf_data, dict):
            if not format.startswith(APPLICATION_LD_JSON):
                raise ValueError(
                    f"Expected format {APPLICATION_LD_JSON} for dict input, got {format}"
                )
            #
            # I just want to get the dict, with an empty graph.
            #
            super().__init__("")
            self.json_ld = rdf_data
            self.graph = to_rdf(rdf_data, self.graph)
        else:
            raise ValueError(f"Unsupported rdf_data type: {type(rdf_data)}")

        if not frame.validate(strict=True):
            raise ValueError(f"Invalid frame: {frame}")

        self.frame = frame
        self._already_framed = bool(format == APPLICATION_LD_JSON_FRAMED)

    def create_api_data(self, sample=False) -> JsonLD:
        """
        Frame the RDF data according to the provided JSON-LD frame.

        Returns:
            dict: Framed JSON-LD data ready for API output
        """
        callbacks: Iterable[JsonLDFunction] = [
            lambda framed: {
                "@context": framed["@context"],
                "@graph": [
                    _remove_jsonld_keys(item)
                    for item in framed.get("@graph", [])
                ],
            },
        ]
        if not self._already_framed:
            data: JsonLD = self.project(
                self.frame,
            )
        else:
            log.info("Data is already framed, skipping framing step")
            data = self.json_ld

        for callback in callbacks:
            ts = time.time()
            log.debug("Applying callback %s to framed data", callback)
            _data: JsonLD | None = callback(data)
            if _data is not None:
                data = _data
            log.debug(
                "Callback %s took %.2f seconds", callback, time.time() - ts
            )

        assert "@graph" in data
        assert "@context" in data
        return data

    def api_uuid(self) -> str:
        """
        API require agencyId and keyConcept.
        """
        from tools.store import build_vocabulary_uuid

        metadata: VocabularyMetadata = self.metadata()
        if metadata.name is None or metadata.agency_id is None:
            raise ValueError(
                "Vocabulary metadata must include non-empty 'name' and 'agency_id' for API UUID generation"
            )
        return build_vocabulary_uuid(
            agency_id=metadata.agency_id,
            key_concept=metadata.name,
        )

    def to_db(
        self,
        data: JsonLD,
        datafile: Path,
        force: bool = False,
        openapi: OpenAPI = EmptyOpenAPI,
    ) -> None:
        from tools.store import APIStore

        assert data
        metadata: VocabularyMetadata = self.metadata()
        if metadata.name is None or metadata.agency_id is None:
            raise ValueError(
                "Vocabulary metadata must include non-empty 'name' and 'agency_id'"
            )
        if force and datafile.exists():
            datafile.unlink()
        with APIStore(str(datafile)) as db:
            db.create_metadata_table()
            db.upsert_metadata(
                vocabulary_uri=self.uri() or "",
                agency_id=metadata.agency_id,
                key_concept=metadata.name,
                openapi=openapi,
                catalog=self.catalog_entry(),
            )
            db.update_vocabulary_from_jsonld(
                metadata.agency_id,
                metadata.name,
                data["@graph"],
            )

    def from_db(self, datafile: Path) -> JsonLD:
        from tools.store import APIStore

        metadata: VocabularyMetadata = self.metadata()
        if metadata.name is None or metadata.agency_id is None:
            raise ValueError(
                "Vocabulary metadata must include non-empty 'name' and 'agency_id'"
            )

        with APIStore(str(datafile)) as db:
            return cast(
                JsonLD,
                db.get_vocabulary_jsonld(
                    metadata.agency_id,
                    metadata.name,
                    self.frame.context,
                ),
            )

    def catalog_entry(self) -> dict[str, Any]:
        """
        Return a dictionary representing this vocabulary as an entry in the API catalog.

        The returned dictionary includes properties such as 'href', 'about', 'title', 'description', 'hreflang', 'version', 'author', and relations like 'service-desc' and 'predecessor-version'.
        """
        metadata: VocabularyMetadata = self.metadata()
        if metadata.name is None or metadata.agency_id is None:
            raise ValueError(
                "Vocabulary metadata must include non-empty 'name' and 'agency_id'"
            )

        return {
            "about": self.uri(),
            "title": metadata.title,
            "description": metadata.description,
            "hreflang": metadata.languages(),
            # "type": "application/json",
            "version": metadata.version,
            "author": metadata.rights_holder,
        }

    def json_schema(
        self,
        schema_instances: JsonLD,
        add_constraints=True,
        validate_output=True,
    ) -> OpenAPI:
        """
        Generate an OpenAPI schema from the framed RDF data.

        This method frames the RDF data according to the provided JSON-LD frame,
        then infers a JSON Schema from the framed data, and finally enhances
        the schema with constraints derived from the JSON-LD context.

        Args:
        - schema_instances: The framed JSON-LD data to use as samples for schema inference
        - add_constraints: Whether to add validation constraints from the JSON-LD context
        - validate_output: Whether to validate the framed data against the generated schema and include results in
            x-validation.
        Returns:
            OpenAPI: OpenAPI schema inferred from framed samples
        """
        assert schema_instances
        return create_schema_from_frame_and_data(
            self.frame,
            schema_instances,
            add_constraints=add_constraints,
            validate_output=validate_output,
        )

    def openapi(self, **kwargs) -> OpenAPI:
        """
        Return an OAS 3.0 document which includes the Vocabulary metadata
        together with the generated OpenAPI schema.
        """
        metadata: VocabularyMetadata = self.metadata()
        contact = {"url": metadata.rights_holder}
        metadata_contact_name = metadata.contact_name
        metadata_contact_email = metadata.contact_email
        if metadata_contact_name is not None:
            contact["name"] = metadata_contact_name
        if metadata_contact_email is not None:
            contact["email"] = metadata_contact_email

        schema_instances: JsonLD = self.create_api_data()
        assert schema_instances, "Expected non-empty schema instances"
        schema = self.json_schema(
            schema_instances=schema_instances,
            **kwargs,
        )
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": metadata.title,
                "version": metadata.version or "1.0.0",
                "description": metadata.description or "",
                "x-summary": metadata.get_first_value(
                    [
                        DCTERMS.abstract,
                    ],
                    lang=LANG_NONE,
                )
                or "",
                "contact": contact,
                #
                # Backward compatibility with API v0.
                #
                "x-keyConcept": metadata.name,
                "x-agencyId": metadata.agency_id,
            },
            "paths": {},
            "servers": [],
            "components": {"schemas": {"Item": schema}},
        }

        validate(instance=openapi, schema=OAS30_SCHEMA)
        return cast(OpenAPI, openapi)

    # self.json_schema(**kwargs)


def create_schema_from_frame_and_data(
    frame: JsonLDFrame,
    framed: JsonLD,
    add_constraints=True,
    validate_output=True,
) -> OpenAPI:
    """
    Sample-based approach: Frame the RDF data and infer schema from result.

    Generate the OAS 3.0 schema based on actual
    data rather than heuristics.
    The design is intentionally strict, trying to be
    as deterministic as possible even for dataset created
    by different organizations.

    Args:
        frame: JSON-LD frame specification
        framed: Framed JSON-LD data

    Returns:
        OpenAPI: OpenAPI schema inferred from framed samples
    """

    if not frame.validate(strict=True):
        raise ValueError(f"Invalid frame: {frame}")

    if not framed:
        raise ValueError(f"No framed data: {framed}")

    # Extract the graph array (JSON-LD framed output format)
    if _graph := framed.get("@graph"):
        samples = _graph
    elif "@type" in framed:
        samples = [framed]
    else:
        raise NotImplementedError(
            "Framed data must be a JSON-LD dictionary or a single object with @type."
        )

    # Infer schema from normalized samples
    schema = infer_schema_from_samples(samples)

    # Add constraints from JSON-LD context
    if add_constraints:
        schema = add_constraints_from_context(schema, frame)

    # Add JSON-LD context as extension
    schema["x-jsonld-context"] = frame.context
    if "@type" in frame:
        schema["x-jsonld-type"] = (
            frame["@type"]
            if isinstance(frame["@type"], str)
            else frame["@type"][0]
        )

    # Add an example entry, that can be used
    #   inside the Schema Editor, eventually
    #   removing @type.
    schema["example"] = samples[0]

    # Validate the framed data against the schema
    if validate_output:
        is_valid, errors = validate_data_against_schema(samples, schema)
        schema["x-validation"] = {
            "valid": is_valid,
            "error_count": len(errors),
            "errors": errors[:10] if errors else [],  # Include first 10 errors
        }

        if errors:
            log.warning(
                "Validation found %d errors in framed data", len(errors)
            )
            for error in errors[:3]:  # Log first 3 errors
                log.warning(
                    "Validation error: %s at path %s",
                    error["message"],
                    error["path"],
                )

    return cast(OpenAPI, schema)


def infer_schema_from_samples(samples):
    """
    Generate JSON Schema from sample data using genson.

    Idea: Consider subsampling to speed it up.

    Args:
        samples: A list of sample objects or a single sample object

    Returns:
        dict: JSON Schema (OpenAPI-compatible)
    """
    builder = OAS3SchemaBuilder()

    if isinstance(samples, list):
        for sample in samples:
            builder.add_object(sample)
    else:
        builder.add_object(samples)

    schema = builder.to_schema()

    # Clean up genson's default schema root
    if "$schema" in schema:
        del schema["$schema"]

    # Ensure the schema is of type object
    if schema.get("type") != "object":
        raise ValueError("Inferred schema is not of type object")

    if "properties" not in schema:
        raise ValueError("Inferred schema has no properties")

    # Sort required properties for consistency
    schema["required"] = sorted(schema["required"])
    return schema


def validate_data_against_schema(data, schema):
    """
    Validate JSON data against a JSON Schema.

    Args:
        data: JSON data to validate (dict or list of dicts)
        schema: JSON Schema to validate against

    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    errors = []

    # Handle both single objects and arrays
    items = data if isinstance(data, list) else [data]

    for idx, item in enumerate(items):
        try:
            validate(instance=item, schema=schema)
        except ValidationError as e:
            errors.append(
                {
                    "index": idx,
                    "path": list(e.path),
                    "message": e.message,
                    "validator": e.validator,
                }
            )

    return len(errors) == 0, errors


def add_url_format_recursively(schema):
    """
    Recursively add format: uri-reference to all 'url' fields in schema.

    Args:
        schema: JSON Schema (or sub-schema) to process

    FIXME: Use `uri` (absolute) instead of `uri-reference` (relative)
    """
    if not isinstance(schema, dict):
        return

    # Process properties at current level
    if "properties" in schema:
        for field_name, prop_schema in schema["properties"].items():
            if field_name == URI and prop_schema.get("type") == "string":
                prop_schema["format"] = "uri-reference"
            # Recurse into nested objects
            if prop_schema.get("type") == "object":
                add_url_format_recursively(prop_schema)
            # Recurse into array items
            elif prop_schema.get("type") == "array" and "items" in prop_schema:
                add_url_format_recursively(prop_schema["items"])

    # Also handle schemas that might be at the root level
    if schema.get("type") == "object" and "properties" not in schema:
        # Edge case: object without explicit properties
        pass


def add_constraints_from_context(schema, frame):
    """
    Enhance JSON Schema with constraints derived from JSON-LD context.

    This analyzes the JSON-LD @context to add validation constraints:
    - XSD type coercion → JSON Schema types with constraints
    - SKOS notation → pattern constraints
    - Language tags → string constraints
    - Container types → array constraints

    Args:
        schema: Base JSON Schema to enhance
        frame: JSON-LD frame with @context

    Returns:
        dict: Enhanced schema with constraints
    """
    # First, recursively add format: uri to all 'url' fields
    add_url_format_recursively(schema)

    context = frame.context
    properties = schema.get("properties", {})

    for field, prop_schema in properties.items():
        # Skip if not in context
        if field not in context:
            continue

        context_def = context[field]

        # Handle string context definitions (just URIs)
        if isinstance(context_def, str):
            if context_def == "@id":
                continue
            context_def = {"@id": context_def}

        # Handle dict context definitions with @type, @id, etc.
        if not isinstance(context_def, dict):
            continue

        # Add constraints based on @type (XSD type coercion)
        if "@type" in context_def:
            xsd_type = context_def["@type"]

            if "integer" in xsd_type or "int" in xsd_type:
                if prop_schema.get("type") in ["integer", "number"]:
                    prop_schema["minimum"] = 0
                    # Add constraint that level should be reasonable
                    if field == "level":
                        prop_schema["maximum"] = 10

            elif "string" in xsd_type:
                if prop_schema.get("type") == "string":
                    prop_schema["minLength"] = 1

        # Add constraints based on @id (property semantics)
        predicate = context_def["@id"]

        log.debug("Field '%s' has predicate '%s'", field, predicate)

        # SKOS notation constraints
        if predicate.endswith(("notation", "identifier")):
            if prop_schema.get("type") == "string":
                log.debug("Adding notation constraints to field '%s'", field)
                prop_schema["pattern"] = "^[A-Za-z0-9._-]+$"
                prop_schema["minLength"] = 1

        # SKOS prefLabel or RDFS label default constraints
        elif predicate.endswith(("prefLabel", "label")):
            if prop_schema.get("type") == "string":
                prop_schema["minLength"] = 1
                prop_schema["maxLength"] = 500

        # Add constraints for language-tagged strings
        if "@language" in context_def:
            if prop_schema.get("type") == "string":
                prop_schema["minLength"] = 1

        # Add constraints for @container: @set (arrays)
        if context_def.get("@container") in ("@set", "@list"):
            if prop_schema.get("type") != "array":
                raise ValueError(
                    f"Field '{field}' expected to be array due to @container but is not"
                )
    return schema
