class CacheControlResponseHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, environ, start_response):
        response = self.app(environ, start_response)
        if (
            (response.headers.get("Cache-Control") is not None)
            or (response.status_code != 200)
            or (response.method != "GET")
        ):
            return response

        response.headers.add("Cache-Control", "max-age=3600")
        # start_response("200 OK", [("Cache-Control", "max-age=3600")])
        return response
