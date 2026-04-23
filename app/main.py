import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.routers.flow import router as flow_router
from app.scrapers.edgar import close_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_client()


app = FastAPI(
    title="sec-flow",
    version="1.0.0",
    description="SEC EDGAR insider flow tracker — Form 4, 13F, XBRL concepts, full-text search.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(flow_router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}
