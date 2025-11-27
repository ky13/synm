"""Health check endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from sanctum.core.database import get_db
from sanctum.services.chroma_service import ChromaService
from sanctum.services.redis_service import RedisService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "sanctum",
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with component status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
    }
    
    # Check database
    try:
        async with get_db() as db:
            result = await db.execute(text("SELECT 1"))
            _ = result.scalar()
        health_status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis_service = RedisService()
        await redis_service.ping()
        health_status["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"
    
    # Check Chroma
    try:
        chroma_service = ChromaService()
        await chroma_service.health_check()
        health_status["components"]["chroma"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Chroma health check failed: {e}")
        health_status["components"]["chroma"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"
    
    # Return 503 if unhealthy
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """Readiness check for container orchestration."""
    # Perform basic checks to ensure service is ready
    try:
        async with get_db() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail={"status": "not_ready", "error": str(e)})