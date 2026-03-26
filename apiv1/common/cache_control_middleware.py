from collections.abc import Callable
from typing import Any


class CacheControlResponseHeaderMiddleware:
    @staticmethod
    def factory(
        max_age: int = 3600,
    ) -> Callable[[Any], "CacheControlResponseHeaderMiddleware"]:
        """
        Factory method to create an instance of the middleware with the specified max_age.

        Args:
            max_age: The max-age value for the Cache-Control header in seconds.

        Returns:
            A callable that can be used as middleware in a Connexion app.
        """
        return lambda app: CacheControlResponseHeaderMiddleware(app, max_age)

    def __init__(self, app, max_age):
        self.app = app
        self.max_age = max_age

        # Assemble the Cache-Control header value once, since it's the same for all responses.
        self._cache_control_value = f"max-age={max_age}".encode()

    async def __call__(self, scope, receive, send):
        # We only care about HTTP responses
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_cache_control(message):
            if message["type"] == "http.response.start":
                # Headers are a list of (name, value) tuples in bytes
                headers = list(message.get("headers", []))
                headers.append((b"cache-control", self._cache_control_value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_cache_control)
