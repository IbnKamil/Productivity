from __future__ import annotations

import time
from uuid import uuid4

import sentry_sdk
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from app.api import routes_auth, routes_goals, routes_sessions, routes_settings, routes_stats, routes_tasks
from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.models import *  # noqa: F403 - ensure SQLAlchemy models are imported for Alembic metadata.

configure_logging()
settings = get_settings()
logger = structlog.get_logger()

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["method", "path"])

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router)
app.include_router(routes_goals.router)
app.include_router(routes_tasks.router)
app.include_router(routes_sessions.router)
app.include_router(routes_stats.router)
app.include_router(routes_settings.router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    correlation_id = request.headers.get("x-correlation-id", request_id)
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    start = time.perf_counter()
    status_code = 500
    response = await call_next(request)
    status_code = response.status_code
    duration = time.perf_counter() - start
    REQUEST_COUNT.labels(request.method, request.url.path, str(status_code)).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(duration)
    logger.info(
        "request.completed",
        request_id=request_id,
        correlation_id=correlation_id,
        method=request.method,
        endpoint=request.url.path,
        duration=round(duration, 4),
        status=status_code,
        user_id=getattr(getattr(request.state, "user", None), "id", None),
    )
    response.headers["x-request-id"] = request_id
    response.headers["x-correlation-id"] = correlation_id
    return response


def _error(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message},
            "request_id": request.state.request_id,
            "correlation_id": request.state.correlation_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return _error(request, exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error(request, 422, "validation_error", str(exc.errors()))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("request.failed", request_id=request.state.request_id, error=str(exc))
    return _error(request, 500, "internal_error", "Unexpected server error")


@app.get("/health")
def health(request: Request):
    return {
        "success": True,
        "data": {"status": "ok"},
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
    }


@app.get("/ready")
def ready(request: Request):
    with engine.connect() as connection:
        connection.execute(text("select 1"))
    return {
        "success": True,
        "data": {"status": "ready"},
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
    }


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
