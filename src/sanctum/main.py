"""Main FastAPI application for Sanctum Personal AI Vault."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import make_asgi_app

from sanctum.api import auth, context, health, sessions
from sanctum.config import get_settings
from sanctum.core.database import init_db
from sanctum.utils.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Sanctum Personal AI Vault...")
    
    # Initialize database
    await init_db()
    
    # Initialize services
    logger.info("Initializing services...")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Sanctum Personal AI Vault...")


# Create FastAPI app
app = FastAPI(
    title="Sanctum Personal AI Vault",
    description="Privacy-first memory keeper for AI interactions",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.log_level == "DEBUG" else None,
    redoc_url="/redoc" if settings.log_level == "DEBUG" else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/v1", tags=["sessions"])
app.include_router(context.router, prefix="/v1", tags=["context"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Sanctum Personal AI Vault",
        "version": "0.1.0",
        "status": "operational",
    }