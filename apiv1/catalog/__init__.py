"""
Catalog API package initialization.
"""

from .app import Config, create_app

__all__ = ["create_app", "Config"]
