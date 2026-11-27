"""Điểm khởi tạo FastAPI cho BookHub Web Backend."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes.health import router as health_router
from backend.config import load_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Tạo ứng dụng FastAPI theo cấu hình môi trường hiện tại."""
    settings = load_settings()
    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled API error for %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Đã xảy ra lỗi nội bộ. Vui lòng thử lại sau."},
        )

    app.include_router(health_router, prefix=settings.api_prefix)
    return app


app = create_app()
