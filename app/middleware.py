from fastapi import FastAPI, Request

_DOCS = ("/docs", "/redoc", "/openapi.json")


def add_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"  # dado de saúde não fica em cache
        if not request.url.path.startswith(_DOCS):  # Swagger precisa de CDN
            resp.headers["Content-Security-Policy"] = (
                "default-src 'none'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            )
        return resp
