from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .._metadata import api_prefix, dist_dir
from .logger import logger


def add_not_found_handler(app: FastAPI):
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.info(
            f"HTTP exception handler called for request {request.url.path} with status code {exc.status_code}"
        )
        if exc.status_code == 404:
            path = request.url.path
            accept = request.headers.get("accept", "")

            is_api = path.startswith(api_prefix)
            is_get_page_nav = request.method == "GET" and "text/html" in accept
            looks_like_asset = "." in path.split("/")[-1]

            if (not is_api) and is_get_page_nav and (not looks_like_asset):
                return FileResponse(dist_dir / "index.html")
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.exception_handler(StarletteHTTPException)(http_exception_handler)
