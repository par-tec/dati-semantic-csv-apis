"""Shared exception handlers for the API services."""

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
    """Build a size-constrained application/problem+json response."""
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
        # Safely ignore additional kwargs.
    )


def bad_request(
    request: ConnexionRequest, error: BadRequestProblem
) -> ConnexionResponse:
    """Handle BadRequestProblem exceptions and return a 400 response."""
    return safe_problem(
        status=400,
        title="Bad Request",
        detail=str(error),
    )


def handle_problem_safe(
    request: ConnexionRequest, error: ProblemException
) -> ConnexionResponse:
    """Handle connexion ProblemException responses without exposing internals."""
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
    """Handle unexpected exceptions and return a generic 500 response."""
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
    """Handle NotImplementedError exceptions and return a 501 response."""
    logger.exception("NotImplementedError: %s", str(error), exc_info=error)

    return safe_problem(
        status=501,
        title="Not Implemented",
        detail=str(error),
        instance=str(request.url),
        headers={"Content-Type": "application/problem+json"},
    )
