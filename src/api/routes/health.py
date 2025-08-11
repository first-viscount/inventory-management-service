"""Health check endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    description="""
Check the health of the Inventory Management Service.

This endpoint provides a basic health check that includes:
- Service status (always "healthy" if endpoint is reachable)
- Database connectivity status
- Service version information

Used by load balancers and monitoring systems to determine service health.
    """,
    response_description="Service health status",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "inventory-management-service",
                        "version": "0.1.0",
                        "database": "connected",
                    }
                }
            },
        }
    },
    status_code=status.HTTP_200_OK,
    tags=["health"],
)
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Basic health check."""
    from src.core.config import settings

    # Test database connection
    try:
        await db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        database_status = "disconnected"

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": database_status,
    }


@router.get(
    "/health/ready",
    summary="Readiness Check",
    description="""
Check if the service is ready to handle requests.

This is a more comprehensive health check that verifies:
- Database connection is working
- All required dependencies are available
- Service is properly initialized

Returns 200 if ready, 503 if not ready.
Used by Kubernetes readiness probes.
    """,
    response_description="Service readiness status",
    responses={
        200: {
            "description": "Service is ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "service": "inventory-management-service",
                        "version": "0.1.0",
                        "checks": {
                            "database": "ok"
                        },
                    }
                }
            },
        },
        503: {
            "description": "Service is not ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "not_ready",
                        "service": "inventory-management-service",
                        "version": "0.1.0",
                        "checks": {
                            "database": "failed"
                        },
                    }
                }
            },
        },
    },
    tags=["health"],
)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Readiness check for Kubernetes."""
    from src.core.config import settings

    checks = {}
    all_ready = True

    # Test database connection
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Database readiness check failed", error=str(e))
        checks["database"] = "failed"
        all_ready = False

    response = {
        "status": "ready" if all_ready else "not_ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "checks": checks,
    }

    if not all_ready:
        # Return 503 if not ready
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=response)

    return response


@router.get(
    "/health/live",
    summary="Liveness Check",
    description="""
Check if the service is alive and running.

This is a basic liveness check that only verifies the service process is running.
Does not check dependencies like database connections.

Always returns 200 OK if the endpoint is reachable.
Used by Kubernetes liveness probes.
    """,
    response_description="Service liveness status",
    responses={
        200: {
            "description": "Service is alive",
            "content": {
                "application/json": {
                    "example": {
                        "status": "alive",
                        "service": "inventory-management-service",
                        "version": "0.1.0",
                    }
                }
            },
        }
    },
    status_code=status.HTTP_200_OK,
    tags=["health"],
)
async def liveness_check() -> dict[str, str]:
    """Liveness check for Kubernetes."""
    from src.core.config import settings

    return {
        "status": "alive",
        "service": settings.app_name,
        "version": settings.app_version,
    }