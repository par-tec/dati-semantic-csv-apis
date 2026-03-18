"""Connexion middleware for validating printable request parameters."""

from collections.abc import Iterable
from typing import Any

from connexion.exceptions import BadRequestProblem
from connexion.lifecycle import ConnexionRequest


class PrintableParametersMiddleware:
    """Reject requests whose path/query parameter values contain non-printable chars."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self, scope: dict[str, Any], receive: Any, send: Any
    ) -> None:
        if scope.get("type") == "http":
            self._validate_request_parameters(scope)
        await self.app(scope, receive, send)

    def _validate_request_parameters(self, scope: dict[str, Any]) -> None:
        request = ConnexionRequest(scope)
        invalid_parameters: list[str] = []

        for name, value in request.query_params.multi_items():
            if not self._is_printable(value):
                invalid_parameters.append(f"query.{name}")

        for name, value in request.path_params.items():
            if not self._is_printable(value):
                invalid_parameters.append(f"path.{name}")

        if invalid_parameters:
            details = ", ".join(sorted(set(invalid_parameters)))
            raise BadRequestProblem(
                detail=(
                    "Non-printable characters found in request parameters: "
                    f"{details}"
                )
            )

    @staticmethod
    def _is_printable(value: Any) -> bool:
        if value is None:
            return True

        if isinstance(value, str):
            return value.isprintable()

        if isinstance(value, Iterable) and not isinstance(
            value, (bytes, bytearray)
        ):
            return all(
                PrintableParametersMiddleware._is_printable(item)
                for item in value
            )

        return str(value).isprintable()
