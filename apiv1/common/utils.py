from typing import cast

from connexion import request

from tools.store import APIStore


def _get_database_or_fail() -> APIStore:
    """Return the configured read-only APIStore instance."""
    harvest_db = cast(
        APIStore | None,
        getattr(request.state, "harvest_db", None),
    )
    if harvest_db is None:
        raise ValueError("Harvest DB not configured")
    return harvest_db
