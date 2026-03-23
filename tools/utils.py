"""
Test expanding JSON-LD context entries to absolute URIs.
"""

import logging
import time

import yaml
from pyld import jsonld
from rdflib import Graph
from rdflib.compare import IsomorphicGraph, to_isomorphic

log = logging.getLogger(__name__)


class IGraph:
    @staticmethod
    def parse(source=None, data=None, **kwargs) -> IsomorphicGraph:
        try:
            ts = time.time()
            g = Graph()
            g.parse(source=source, data=data, **kwargs)
            assert len(g) > 0, "Parsed RDF graph is empty"
            log.debug(
                f"Parsed RDF graph with {len(g)} triples in {time.time() - ts:.3f}s"
            )
            return to_isomorphic(g)
        except Exception as e:
            log.exception(f"Failed to parse RDF data: {kwargs}")
            raise e


class SafeQuotedStringDumper(yaml.SafeDumper):
    """Custom YAML dumper that quotes all string values."""

    pass


def quoted_string_representer(dumper, data):
    """Represent strings with conditional quoting based on length."""
    if len(data) < 16:
        # Don't quote
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)
    elif len(data) < 120:
        # Use folded scalar style (>)
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    else:
        # Use literal scalar style (|)
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


SafeQuotedStringDumper.add_representer(str, quoted_string_representer)


def expand_context_to_absolute_uris(context: dict) -> dict:
    """
    Convert JSON-LD context entries from compact IRIs to absolute URIs.

    Examples:
        Input context:
            {
                "skos": "https://example.org/skos#",
                "@vocab": "https://w3id.org/italia/onto/CPV/",
                "p": "Person",
                "id": "skos:notation",
                "label": {"@id": "skos:prefLabel", "@language": "it"}
            }

        Output:
            {
                "p": "https://w3id.org/italia/onto/CPV/Person",
                "id": "https://example.org/skos#notation",
                "label": {"@id": "https://example.org/skos#prefLabel", "@language": "it"}
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
        return value.startswith(("http://", "https://", "urn:", "mailto:"))

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

        # Handle dictionary values with @id and other properties
        if isinstance(value, dict) and "@id" in value:
            # Create a minimal document to expand just the @id
            doc = {"@context": context, key: "dummy"}
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
                        # If the dict only has @id, return just the expanded URI
                        if len(value) == 1:
                            expanded[key] = prop_iri
                        else:
                            # Otherwise preserve the dictionary structure with expanded @id
                            expanded[key] = value.copy()
                            expanded[key]["@id"] = prop_iri
                        break
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
