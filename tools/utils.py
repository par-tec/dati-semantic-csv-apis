"""
Test expanding JSON-LD context entries to absolute URIs.
"""

import logging

import yaml
from pyld import jsonld
from rdflib import Graph
from rdflib.compare import IsomorphicGraph, to_isomorphic

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class IGraph:
    @staticmethod
    def parse(*args, **kwargs) -> IsomorphicGraph:
        try:
            g = Graph()
            g.parse(*args, **kwargs)
            return to_isomorphic(g)
        except Exception as e:
            log.exception(f"Failed to parse RDF data: {args}, {kwargs}")
            raise e


class QuotedStringDumper(yaml.SafeDumper):
    """Custom YAML dumper that quotes all string values."""

    pass


def quoted_string_representer(dumper, data):
    """Represent strings with double quotes."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


QuotedStringDumper.add_representer(str, quoted_string_representer)


def expand_context_to_absolute_uris(context: dict) -> dict:
    """
    Convert JSON-LD context entries from compact IRIs to absolute URIs.

    Examples:
        Input context:
            {
                "skos": "https://example.org/skos#",
                "@vocab": "https://w3id.org/italia/onto/CPV/",
                "p": "Person",
                "id": "skos:notation"
            }

        Output:
            {
                "p": "https://w3id.org/italia/onto/CPV/Person",
                "id": "https://example.org/skos#notation"
            }

    Args:
        context: JSON-LD context with prefixes and compact IRIs

    Returns:
        dict: Context with all entries expanded to absolute URIs
    """
    expanded = {}

    def is_prefix_declaration(value):
        """Check if a value is a prefix declaration (namespace URI)."""
        if not isinstance(value, str):
            return False
        # Prefix declarations are typically absolute URIs
        return value.startswith(("http://", "https://", "urn:"))

    for key, value in context.items():
        # Skip special JSON-LD keywords
        if key.startswith("@"):
            continue

        # Skip prefix declarations (e.g., "skos": "http://...")
        if is_prefix_declaration(value):
            continue

        # Skip @id mappings (e.g., "url": "@id")
        if value == "@id":
            continue

        # Create a minimal document to expand
        doc = {"@context": context, key: "dummy"}

        # Expand the document
        expanded_doc = jsonld.expand(doc)

        # Extract the expanded property IRI
        if (
            expanded_doc
            and isinstance(expanded_doc, list)
            and len(expanded_doc) > 0
        ):
            expanded_props = expanded_doc[0]
            # Get the first (and should be only) expanded property key
            for prop_iri in expanded_props.keys():
                if not prop_iri.startswith("@"):
                    expanded[key] = prop_iri
                    break

    return expanded
