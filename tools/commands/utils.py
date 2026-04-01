import logging
from pathlib import Path

import click

log = logging.getLogger(__name__)


def check_output_file(output: Path, force: bool) -> None:
    """Abort if output file exists and --force is not set."""
    if output.exists():
        if not force:
            click.secho(
                f"✗ Error: Output file {output} already exists. Use --force/-f to overwrite.",
                fg="red",
                err=True,
            )
            raise click.Abort()
        log.debug("Overwriting existing file: %s", output)
