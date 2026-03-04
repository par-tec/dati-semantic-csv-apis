"""
Vocabularies API application using Connexion.

This module provides a spec-first API for serving controlled vocabularies
in RFC 9727 linkset format.
"""

from pathlib import Path

from connexion import AsyncApp

app = AsyncApp(
    __name__,
    specification_dir=str(Path(__file__).parent),
)

# Add OpenAPI specification
app.add_api(
    "openapi.yaml",
    # base_path="/",
    strict_validation=True,
    # validate_responses=True,
)
