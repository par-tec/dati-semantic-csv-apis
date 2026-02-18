"""
Sample-based JSON Schema generation from JSON-LD frames and RDF data.

This module provides functions to generate OpenAPI-compatible JSON schemas
by framing RDF data and analyzing the resulting JSON structure.
"""


def frame_context_fields(frame) -> list:
    """
    Extract field names from a JSON-LD frame's @context.

    """

    def is_field(k, v):
        if k.startswith("@"):
            return False
        if isinstance(v, str) and v.startswith("http"):
            return False
        return True

    context_fields = [k for k, v in frame.get("@context", {}).items() if is_field(k, v)]
    default_fields = [
        k for k, v in frame.items() if isinstance(v, dict) and "@default" in v
    ]
    detached_fields = [k for k, v in frame.items() if isinstance(v, dict) and v is None]
    return list(set(context_fields + default_fields + detached_fields))
