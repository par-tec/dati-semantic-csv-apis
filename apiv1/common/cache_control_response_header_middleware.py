class CacheControlResponseHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, environ, start_response):
        response = self.app(environ, start_response)
        start_response("200 OK", [("Cache-Control", "max-age=3600")])
        return response
