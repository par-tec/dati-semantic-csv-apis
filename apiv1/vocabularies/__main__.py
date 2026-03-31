import logging

import uvicorn

from .asgi import application

log = logging.getLogger(__name__)


if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", port=8080)
