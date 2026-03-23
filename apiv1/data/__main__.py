import logging
import os

from connexion import AsyncApp

from . import Config, create_app

log = logging.getLogger(__name__)


if __name__ == "__main__":
    api_base_url = os.getenv("API_BASE_URL") or "http://localhost:8080"
    harvest_db = os.getenv("HARVEST_DB", "harvest.db")

    app: AsyncApp = create_app(
        config=Config(
            API_BASE_URL=api_base_url,
            HARVEST_DB=harvest_db,
        )
    )
    app.run(host="0.0.0.0", port=8080)
