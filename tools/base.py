import datetime
import importlib
import logging
from decimal import Decimal
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

from tools.utils import expand_context_to_absolute_uris

log = logging.getLogger(__name__)

TEXT_TURTLE = "text/turtle"
OX_TURTLE = "ox-turtle"
APPLICATION_LD_JSON = "application/ld+json"
APPLICATION_LD_JSON_FRAME = (
    APPLICATION_LD_JSON + '; profile="http://www.w3.org/ns/json-ld#frame"'
)
APPLICATION_LD_JSON_CONTEXT = (
    APPLICATION_LD_JSON + '; profile="http://www.w3.org/ns/json-ld#context"'
)
APPLICATION_LD_JSON_FRAMED = (
    APPLICATION_LD_JSON + '; profile="http://www.w3.org/ns/json-ld#framed"'
)
DATADIR: Traversable = importlib.resources.files(__name__) / "data"


JsonScalar = (int, float, bool, str, type(None))
DbScalar = JsonScalar + (bytes,)  # SQLite-compatible
FullScalar = JsonScalar + (
    datetime.date,
    datetime.datetime,
    Decimal,
)  # Extended scalar types for JSON-LD data

JsonLD = TypedDict(
    "JsonLD",
    {"@context": dict, "@graph": list, "statistics": dict},
    total=False,
)
type RDFText = str
type JSONLDText = str


class JsonLDFrame(dict):
    """
    JSON-LD Frame dictionary with helper methods.

    A frame is used to shape JSON-LD data, typically containing at minimum
    a @context field that defines the vocabulary and structure.

    This class extends dict to maintain full compatibility with existing code
    while providing convenient methods for common JSON-LD frame operations.
    """

    def __init__(self, *args, **kwargs):
        """Initialize JsonLDFrame from dict or keyword arguments."""
        super().__init__(*args, **kwargs)

    @property
    def context(self) -> dict[str, Any]:
        """Get the @context field, returning empty dict if not present."""
        return cast(dict[str, Any], self.get("@context", {}))

    @context.setter
    def context(self, value: dict[str, Any]) -> None:
        """Set the @context field."""
        self["@context"] = value

    def has_context(self) -> bool:
        """Check if frame has a @context defined."""
        return "@context" in self and bool(self["@context"])

    def merge_context(
        self, additional_context: dict[str, Any]
    ) -> "JsonLDFrame":
        """
        Merge additional context into the existing @context.

        Args:
            additional_context: Context dictionary to merge

        Returns:
            Self for method chaining
        """
        current = self.context
        if isinstance(current, dict):
            current.update(additional_context)
            self["@context"] = current
        return self

    def validate(self, strict: bool = False) -> bool:
        """
        This tool expects that a frame has a specific structure,
        to ensure a consistent output between different datasets.

        1. only one @type is specified, so that the API schema
        corresponds to a single entity type, that should be
        added in the `x-jsonld-type` field of the schema.
        2. referenced entities (e.g., skos:broader, skos:insScheme)
        should be mapped to specific JSON properties;
        3. references to `@id`s should be URIs (strings);
        4. arrays should be explicitly defined using `@container: @set`;

        Args:
            strict: If True, validate context fields against allowed IRIs

        Returns:
            bool: True if valid, False otherwise

        Raises:
            ValueError: In strict mode if field mappings are invalid
        """
        # Check if @type exists
        _type = self.get("@type")
        if not _type:
            log.error("Frame must specify an @type")
            return False

        # Ensure only a single @type is specified
        if isinstance(_type, list) and len(_type) > 1:
            log.error(
                "Frame must specify a single @type, found list: %s", _type
            )
            return False

        # Strict mode: validate context field mappings
        if strict:
            ALLOWED_VALUES = {
                "id": [
                    "http://www.w3.org/2004/02/skos/core#notation",
                    "http://purl.org/dc/terms/identifier",
                    "http://purl.org/dc/elements/1.1/identifier",
                ],
                "label": ["http://www.w3.org/2004/02/skos/core#prefLabel"],
                #'label_de': ['http://www.w3.org/2004/02/skos/core#prefLabel'],
                #'label_en': ['http://www.w3.org/2004/02/skos/core#prefLabel'],
                #'label_it': ['http://www.w3.org/2004/02/skos/core#prefLabel'],
                "level": [
                    "https://w3id.org/italia/onto/CLV/hasRankOrder",
                    "http://rdf-vocabulary.ddialliance.org/xkos#depth",
                ],
                "parent": ["http://www.w3.org/2004/02/skos/core#broader"],
                "vocab": ["http://www.w3.org/2004/02/skos/core#inScheme"],
            }

            expanded_context = expand_context_to_absolute_uris(self.context)

            for field, definition in expanded_context.items():
                if field not in ALLOWED_VALUES:
                    continue
                expected_iris = ALLOWED_VALUES[field]
                if definition not in expected_iris:
                    raise ValueError(
                        f"Field '{field}' must be one of {expected_iris}, "
                        f"got {definition}"
                    )

        return True

    def copy(self) -> "JsonLDFrame":
        """Return a shallow copy as JsonLDFrame."""
        return JsonLDFrame(super().copy())

    def __repr__(self) -> str:
        """String representation showing it's a JsonLDFrame."""
        return f"JsonLDFrame({dict.__repr__(self)})"

    def pprint(self) -> None:
        """Pretty print the frame for debugging."""
        import yaml

        print(yaml.dump(dict(self), sort_keys=False))

    @staticmethod
    def load(fpath: Path) -> "JsonLDFrame":
        """Load frame from a YAML file."""

        data = yaml.safe_load(fpath.read_text())
        return JsonLDFrame(data)

    def get_fields(self) -> list:
        """
        Extract field names from a JSON-LD frame, including:
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

        context_fields = [k for k, v in self.context.items() if is_field(k, v)]

        default_fields = [
            k
            for k, v in self.items()
            if isinstance(v, dict) and "@default" in v
        ]

        detached_fields = [
            k for k, v in self.items() if isinstance(v, dict) and v is None
        ]

        return list(set(context_fields + default_fields + detached_fields))
