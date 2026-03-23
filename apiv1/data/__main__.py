import logging
import os
from pathlib import Path

from connexion import AsyncApp

from . import Config, create_app

log = logging.getLogger(__name__)


if __name__ == "__main__":
    api_base_url = os.getenv("API_BASE_URL") or "http://localhost:8080"
    vocabulary_datafile = os.getenv("VOCABULARY_DATAFILE") or str(
        Path(__file__).parent.parent.parent
        / "assets"
        / "controlled-vocabularies"
        / "agente_causale"
        / "latest"
        / "agente_causale.data.yaml"
    )

    app: AsyncApp = create_app(
        config=Config(
            API_BASE_URL=api_base_url,
            HARVEST_DB="harvest.db",
        )
    )
    app.run(host="0.0.0.0", port=8080)
