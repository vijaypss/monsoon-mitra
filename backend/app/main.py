"""MonsoonMitra API entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app import __version__
from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import SecurityHeadersMiddleware
from app.routers import alerts, chat, checklist, geocode, health, plan, weather

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("monsoonmitra")

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("startup", version=__version__, llm_enabled=settings.llm_enabled, env=settings.app_env)
    yield
    log.info("shutdown")


app = FastAPI(
    title="MonsoonMitra API",
    version=__version__,
    description="Gen-AI monsoon preparedness for India — plans, alerts, checklists, "
    "travel advisories and a multilingual assistant.",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware (order matters: outermost first) ────────────────────────
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware, is_production=settings.is_production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    max_age=600,
)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Slow down."})


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Never leak internals to the client; log server-side.
    log.error("unhandled_error", path=str(request.url.path), error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# ── Routes ─────────────────────────────────────────────────────────────
API = "/api/v1"
app.include_router(health.router, prefix=API)
app.include_router(geocode.router, prefix=API)
app.include_router(weather.router, prefix=API)
app.include_router(alerts.router, prefix=API)
app.include_router(plan.router, prefix=API)
app.include_router(checklist.router, prefix=API)
app.include_router(chat.router, prefix=API)


@app.get("/")
async def root() -> dict:
    return {"name": "MonsoonMitra", "version": __version__, "docs": "/docs"}
