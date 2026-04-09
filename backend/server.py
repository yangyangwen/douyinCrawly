"""FastAPI HTTP server entrypoint."""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

import click
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel

from .api_errors import register_exception_handlers
from .auth import is_api_auth_enabled, is_request_authorized, unauthorized_response
from .constants import RESOURCE_ROOT, SERVER_DEFAULTS
from .routers import (
    aweme_router,
    aria2_router,
    file_router,
    search_router,
    settings_router,
    system_router,
    task_router,
)
from .sse import sse
from .state import state


class HealthResponse(BaseModel):
    """Health check response."""

    ready: bool
    aria2: bool
    config: bool
    error: str | None


class APIInfoResponse(BaseModel):
    """API info response."""

    name: str
    version: str
    status: str


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifecycle management."""
    logger.info("FastAPI server starting")
    logger.info("Application state initialized")
    if is_api_auth_enabled():
        logger.info("API bearer auth enabled")
    else:
        logger.warning("API bearer auth disabled. Set DOUYIN_API_AUTH_TOKEN to enable it.")

    yield

    logger.info("Cleaning up resources")
    state.cleanup()
    logger.info("Resources cleaned up")


app = FastAPI(
    title="Douyin Collector API",
    description="Douyin collector backend HTTP API",
    version="2.0.0",
    lifespan=lifespan,
)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def bearer_auth_middleware(request: Request, call_next):
    """Protect API and docs endpoints with bearer auth when configured."""
    if not is_request_authorized(request):
        logger.warning(f"Unauthorized request blocked: {request.method} {request.url.path}")
        return unauthorized_response()
    return await call_next(request)


app.include_router(task_router)
app.include_router(aweme_router)
app.include_router(search_router)
app.include_router(settings_router)
app.include_router(aria2_router)
app.include_router(file_router)
app.include_router(system_router)


@app.get("/api", response_model=APIInfoResponse)
def read_root() -> Dict[str, str]:
    """Return API metadata."""
    return {
        "name": "Douyin Collector API",
        "version": "2.0.0",
        "status": "running",
    }


@app.get("/api/health", response_model=HealthResponse)
def health_check() -> Dict[str, Any]:
    """Return backend health status."""
    return state.health_check()


@app.get("/api/events")
async def events_stream():
    """Server-sent events endpoint."""
    return StreamingResponse(
        sse.connect(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


_frontend_dist_dir = os.path.join(RESOURCE_ROOT, "frontend", "dist")

if os.path.exists(_frontend_dist_dir):
    app.mount("/", StaticFiles(directory=_frontend_dist_dir, html=True), name="static")
    logger.info(f"Mounted frontend static assets: {_frontend_dist_dir}")
else:
    logger.warning(f"Frontend dist directory not found: {_frontend_dist_dir}")
    logger.warning("Run `cd frontend && pnpm build` before starting the web server.")


def run_server(
    host: str = SERVER_DEFAULTS["HOST"],
    port: int = SERVER_DEFAULTS["PORT"],
    dev: bool = SERVER_DEFAULTS["DEV"],
) -> None:
    """Start the HTTP server."""
    _run_uvicorn(
        app_target=app if not dev else "backend.server:app",
        host=host,
        port=port,
        reload=dev,
        log_level="info" if dev else "warning",
    )


def _run_uvicorn(
    app_target: Any,
    host: str,
    port: int,
    reload: bool,
    log_level: str,
) -> None:
    """Run uvicorn, avoiding asyncio.run for debugger compatibility."""
    if reload:
        uvicorn.run(
            app_target,
            host=host,
            port=port,
            reload=True,
            log_level=log_level,
        )
        return

    config = uvicorn.Config(
        app_target,
        host=host,
        port=port,
        log_level=log_level,
    )
    server = uvicorn.Server(config)

    with asyncio.Runner(loop_factory=config.get_loop_factory()) as runner:
        runner.run(server.serve())


@click.command()
@click.option(
    "-h",
    "--host",
    type=str,
    default=SERVER_DEFAULTS["HOST"],
    envvar="DOUYIN_HOST",
    help=f"Bind host. Default: {SERVER_DEFAULTS['HOST']}",
)
@click.option(
    "-p",
    "--port",
    type=int,
    default=SERVER_DEFAULTS["PORT"],
    envvar="DOUYIN_PORT",
    help=f"Bind port. Default: {SERVER_DEFAULTS['PORT']}",
)
@click.option(
    "--dev",
    is_flag=True,
    default=SERVER_DEFAULTS["DEV"],
    envvar="DOUYIN_DEV",
    help="Enable development reload mode.",
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug"], case_sensitive=False
    ),
    default=SERVER_DEFAULTS["LOG_LEVEL"],
    envvar="DOUYIN_LOG_LEVEL",
    help=f"Log level. Default: {SERVER_DEFAULTS['LOG_LEVEL']}",
)
def main(host: str, port: int, dev: bool, log_level: str):
    """CLI entrypoint."""
    logger.info("Server configuration")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Dev: {'enabled' if dev else 'disabled'}")
    logger.info(f"  Log level: {log_level}")

    app_target = "backend.server:app" if dev else app

    _run_uvicorn(
        app_target=app_target,
        host=host,
        port=port,
        reload=dev,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
