import logging
import os
from pathlib import Path
from sys import argv

import yaml
from connexion import AsyncApp

from . import Config, create_app
from .download import (
    sparql_query_vocabularies,
    transform_sparql_to_linkset,
)

log = logging.getLogger(__name__)


if __name__ == "__main__":
    sparql_url = os.getenv("SPARQL_URL")
    api_base_url = os.getenv("API_BASE_URL")
    vocabularies_datafile = (
        os.getenv("VOCABULARIES_DATAFILE") or "vocabularies.linkset.yaml"
    )
    if "download" in argv:
        if sparql_url is None:
            print(
                "Error: SPARQL_URL environment variable must be set for download mode."
            )
            raise SystemExit(1)
        if api_base_url is None:
            print(
                "Error: API_BASE_URL environment variable must be set for download mode."
            )
            raise SystemExit(1)

        linkset_data = transform_sparql_to_linkset(
            sparql_query_vocabularies(sparql_url),
            api_base_url,
        )
        linkset_data_yaml = (
            Path(__file__).parent.parent / "vocabularies.linkset.yaml"
        )
        with open(linkset_data_yaml, "w", encoding="utf-8") as f:
            yaml.safe_dump(linkset_data, f)
        print(
            f"Vocabularies linkset data downloaded and saved to: {linkset_data_yaml.absolute().as_posix()}"
        )
        exit(0)
    app: AsyncApp = create_app(
        config=Config(
            SPARQL_URL=sparql_url,
            API_BASE_URL=api_base_url,
            VOCABULARIES_DATAFILE=vocabularies_datafile,
        )
    )
    app.run(host="0.0.0.0", port=8080)
