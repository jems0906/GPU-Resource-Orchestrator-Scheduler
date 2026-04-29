"""
GPU Resource Orchestrator & Scheduler — FastAPI Application Entry Point
"""

import logging
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.api.routes import api_router
from app.db.session import engine
from app.db.base import Base
from app.queue.redis_queue import redis_queue
from app.providers.registry import provider_registry
from app.inventory.manager import inventory_manager
from app.core.scheduler import scheduler
from app.db.session import AsyncSessionLocal

# Configure structured logging
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.LOG_LEVEL)
    )
)
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    # Connect to Redis
    await redis_queue.connect()
    logger.info("Redis connected")

    # Initialize provider registry
    provider_registry.initialize()
    logger.info("Providers initialised: %s", provider_registry.names())

    # Initial inventory sync
    async with AsyncSessionLocal() as db:
        try:
            count = await inventory_manager.sync(db)
            await db.commit()
            logger.info("Initial inventory sync: %d instances loaded", count)
        except Exception as exc:
            logger.warning("Initial inventory sync failed: %s", exc)

    # Start background scheduler
    await scheduler.start()

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down scheduler...")
    await scheduler.stop()

    logger.info("Closing Redis connection...")
    await redis_queue.disconnect()

    logger.info("Disposing database engine...")
    await engine.dispose()

    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "GPU Resource Orchestrator & Scheduler — allocates GPU workloads across "
        "AWS, GCP, and Azure with cost optimization, bin-packing, and SLA enforcement."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    """Service health check."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
