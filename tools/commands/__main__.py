"""
Entry point for running the CLI as a module.

Usage:
    python -m tools.commands jsonld create ...
    python -m tools.commands jsonld validate ...
    python -m tools.commands datapackage create ...
    etc.
"""

from tools.commands import cli

if __name__ == "__main__":
    cli()
