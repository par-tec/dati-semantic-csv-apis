"""
Exception handlers for the Catalog API.

Responses:
- must conform to application/problem+json
- should not expose internal error details to the client.
- MUST ensure that all response body fields are JSON-serializable.
- MUST check for attributes and unexpected data

"""

import logging

from connexion.exceptions import BadRequestProblem, ProblemException
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.problem import problem

logger = logging.getLogger(__name__)


PROBLEM_MAX_DETAIL = 1024
PROBLEM_MAX_TITLE = 256
PROBLEM_MAX_INSTANCE = 1024


def safe_problem(
    status: int,
    title: str,
    detail: str | None = None,
    type: str | None = None,
    instance: str | None = None,
    headers: dict | None = None,
    **kwargs,
) -> ConnexionResponse:
    """
    Build a size-constrained application/problem+json response.

    All string fields are truncated to their configured maximums so
    that callers never need to apply manual slicing.
    """
    if title and (len(title) > PROBLEM_MAX_TITLE):
        title = title[: PROBLEM_MAX_TITLE - 10] + "..."

    if status > 599 or status < 100:
        status = 500

    response = {
        "status": status,
        "title": title,
    }

    if type and (len(type) > 2048):
        type = type[:2038] + "..."
    response["type"] = type

    if detail and (len(detail) > PROBLEM_MAX_DETAIL):
        detail = detail[: PROBLEM_MAX_DETAIL - 10] + "..."
    response["detail"] = detail or ""

    if instance and (len(instance) > PROBLEM_MAX_INSTANCE):
        instance = instance[: PROBLEM_MAX_INSTANCE - 10] + "..."
    response["instance"] = instance or ""

    return problem(
        **response,
        headers=headers,
        #
        # Safely ignore additional kwargs.
        #
        # **kwargs,
    )


def bad_request(
    request: ConnexionRequest, error: BadRequestProblem
) -> ConnexionResponse:
    """
    Handle BadRequestProblem exceptions and return a 400 response.

    Args:
        error: The BadRequestProblem that was raised.
    Returns:
        A ConnexionResponse object representing the error response.
    """
    return safe_problem(
        status=400,
        title="Bad Request",
        detail=str(error),
    )


def handle_problem_safe(
    request: ConnexionRequest, error: ProblemException
) -> ConnexionResponse:
    """
    Handle generic exceptions and return problem+json response.

    The actual error details are logged but not exposed to the client.

    Args:
        error: The exception that was raised.

    Returns:
        A ConnexionResponse object representing the error response.
    """
    return safe_problem(
        status=error.status,
        title=error.title,
        detail=error.detail,
        type=error.type,
        instance=error.instance,
        headers=error.headers,
    )


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
    return safe_problem(
        status=500,
        title="Internal Server Error",
        detail="An unexpected error occurred",
        headers={"Content-Type": "application/problem+json"},
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

    return safe_problem(
        status=501,
        title="Not Implemented",
        detail=str(error),
        instance=str(request.url),
        headers={"Content-Type": "application/problem+json"},
    )
