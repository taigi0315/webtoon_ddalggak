from contextlib import asynccontextmanager
import logging
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.v1.router import api_router
from app.core.settings import settings
from app.core.logging import RequestIdFilter, StructuredJsonFormatter
from app.core.metrics import get_metrics_payload
from app.core.request_context import (
    get_node_name,
    get_scene_id,
    reset_request_id,
    set_request_id,
)
from app.core.telemetry import setup_telemetry
from app.db.base import Base
from app.db.session import get_engine, init_engine
from app.services import job_queue


logger = logging.getLogger("app")


def _is_polling_request(method: str, path: str) -> bool:
    if method != "GET":
        return False
    if path.startswith("/v1/stories/") and path.endswith("/progress"):
        return True
    if path.startswith("/v1/jobs/"):
        return True
    if path.startswith("/v1/scenes/") and (path.endswith("/renders") or path.endswith("/artifacts")):
        return True
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    formatter = StructuredJsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(RequestIdFilter())
    root_logger.addHandler(stream_handler)

    # Reduce noisy access logs; structured request_complete logs are our source of truth.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIdFilter())
        root_logger.addHandler(file_handler)

    init_engine(settings.database_url)

    setup_telemetry(app, service_name="ssuljaengi")

    if settings.db_auto_create and settings.database_url.startswith("sqlite"):
        engine = get_engine()
        Base.metadata.create_all(bind=engine)

    await job_queue.start_worker()
    try:
        yield
    finally:
        await job_queue.stop_worker()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    settings.media_url_prefix,
    StaticFiles(directory=settings.media_root, check_dir=False),
    name="media",
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)
    start = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        request_logger = logger.debug if _is_polling_request(request.method, request.url.path) else logger.info
        request_logger(
            "request_complete",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "node_name": get_node_name(),
                "scene_id": get_scene_id(),
            },
        )
        response.headers["x-request-id"] = request_id
        return response
    finally:
        reset_request_id(token)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "request_id": request_id},
    )


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content={"detail": f"{exc}", "request_id": request_id},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc), "request_id": request_id},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics_endpoint():
    return PlainTextResponse(get_metrics_payload(), media_type="text/plain; version=0.0.4; charset=utf-8")


app.include_router(api_router)
