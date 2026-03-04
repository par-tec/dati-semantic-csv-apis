"""
Exception handlers for the Catalog API.

Responses:
- must conform to application/problem+json
- should not expose internal error details to the client.
- MUST ensure that all response body fields are JSON-serializable.
- MUST check for attributes and unexpected data

"""

import json
import logging

from connexion.lifecycle import ConnexionRequest, ConnexionResponse

logger = logging.getLogger(__name__)


def handle_exception(
    request: ConnexionRequest, error: Exception
) -> ConnexionResponse:
    """
    Handle generic exceptions and return problem+json response.

    The actual error details are logged but not exposed to the client.

    Args:
        error: The exception that was raised.

    Returns:
        A ConnexionResponse object representing the error response.
    """
    logger.exception("Unhandled exception", exc_info=error)

    return ConnexionResponse(
        status_code=500,
        body=json.dumps(
            {
                "type": "about:blank",
                "status": 500,
                "title": "Internal Server Error",
                "detail": "An unexpected error occurred",
            }
        ),
        content_type="application/problem+json",
    )


def handle_not_implemented(
    request: ConnexionRequest, error: NotImplementedError
) -> ConnexionResponse:
    """
    Handle NotImplementedError exceptions and return a 501 response.

    Args:
        error: The NotImplementedError that was raised.
    Returns:
        A ConnexionResponse object representing the error response.
    """
    logger.exception("NotImplementedError: %s", str(error), exc_info=error)

    return ConnexionResponse(
        status_code=501,
        body=json.dumps(
            {
                "type": "about:blank",
                "status": 501,
                "title": "Not Implemented",
                "instance": str(request.url),
            }
        ),
        content_type="application/problem+json",
    )
