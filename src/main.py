"""Main FastAPI application for Inventory Management Service."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.api.middleware.error_handling import (
    ErrorHandlingMiddleware,
    create_exception_handlers,
)
from src.api.middleware.metrics import setup_http_metrics_middleware
from src.api.routes import health, inventory, reservations, locations
from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.logging import get_logger, setup_logging
from src.core.middleware import LoggingMiddleware
from src.core.metrics import service_registry, get_metrics_collector
from src.core.background_metrics import start_background_metrics, stop_background_metrics
from src.core.events import get_event_service, close_event_service

# Setup logging
setup_logging(
    level=settings.log_level,
    service_name=settings.app_name,
    environment=settings.environment,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    # Startup
    logger.info("Starting Inventory Management Service", version=settings.app_version)

    # Initialize database
    if settings.database_url:
        try:
            await init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            # In production, you might want to fail fast here

    # Start background metrics collection
    try:
        await start_background_metrics()
        logger.info("Background metrics collection started")
    except Exception as e:
        logger.error("Failed to start background metrics", error=str(e))
    
    # Initialize event service if enabled
    if settings.events_enabled:
        try:
            await get_event_service()
            logger.info("Event service initialized")
        except Exception as e:
            logger.error("Failed to initialize event service", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down Inventory Management Service")
    
    # Stop background metrics collection
    try:
        await stop_background_metrics()
        logger.info("Background metrics collection stopped")
    except Exception as e:
        logger.error("Failed to stop background metrics", error=str(e))
    
    # Close event service
    if settings.events_enabled:
        try:
            await close_event_service()
            logger.info("Event service closed")
        except Exception as e:
            logger.error("Failed to close event service", error=str(e))
        
    if settings.database_url:
        await close_db()


# Custom OpenAPI schema
def custom_openapi() -> dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## Inventory Management Service API

The Inventory Management Service provides comprehensive inventory tracking and stock management for the First Viscount e-commerce platform.

### Key Features:
- **Real-time Inventory Tracking**: Track available and reserved stock across multiple locations
- **Stock Reservations**: Reserve inventory for orders with automatic expiration
- **Inventory Adjustments**: Handle stock additions, corrections, damage, and other adjustments
- **Multi-location Support**: Manage inventory across warehouses, stores, and other locations
- **Low Stock Alerts**: Identify products below reorder points
- **Audit Trail**: Complete history of all inventory movements and adjustments

### Core Concepts

#### Inventory Locations
The service supports different types of inventory locations:
- **Warehouse**: Distribution centers and fulfillment centers
- **Store**: Physical retail locations
- **Online**: Virtual locations for online-only inventory
- **Dropship**: Supplier locations for dropship items

#### Stock Reservations
When an order is created, inventory can be reserved:
- Moves quantity from "available" to "reserved"
- Has an expiration time (default 1 hour)
- Can be completed (consumed) or released (returned to available)
- Prevents overselling during order processing

#### Inventory Adjustments
Various types of adjustments are supported:
- **Restock**: Adding new inventory
- **Damage**: Recording damaged goods
- **Theft**: Recording inventory loss
- **Correction**: Manual corrections
- **Return**: Processing customer returns
- **Manual**: General manual adjustments

### API Versioning
This API follows semantic versioning. The current version is v1.
- Version is included in the URL path: `/api/v1/...`
- Breaking changes will result in a new major version

### Authentication
Currently, the API is open for development. Authentication will be added in future versions.

### Error Responses
All error responses follow a consistent format:
```json
{
  "error": "ValidationError",
  "message": "Validation failed",
  "details": [...],
  "timestamp": "2025-01-29T12:00:00Z",
  "path": "/api/v1/inventory"
}
```

### Rate Limiting
No rate limiting is currently implemented. This will be added in future versions.
        """,
        routes=app.routes,
        servers=[
            {"url": "http://localhost:8083", "description": "Local development server"},
            {
                "url": "http://inventory-management-service:8083",
                "description": "Docker service",
            },
        ],
    )

    # Add custom error response examples
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "error": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "example": "ValidationError"},
                    "message": {"type": "string", "example": "Validation failed"},
                    "code": {"type": "string", "example": "VALIDATION_ERROR"},
                    "details": {
                        "type": "array",
                        "items": {"type": "object"},
                        "example": [
                            {"field": "quantity", "message": "Quantity must be positive"}
                        ],
                    },
                    "timestamp": {"type": "string", "format": "date-time"},
                    "path": {"type": "string", "example": "/api/v1/inventory"},
                    "request_id": {
                        "type": "string",
                        "example": "550e8400-e29b-41d4-a716-446655440000",
                    },
                },
            }
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Inventory Management Service API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.openapi = custom_openapi  # type: ignore[method-assign]

# Add middleware (order matters - error handling should be outermost)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(setup_http_metrics_middleware())

# Create custom exception handlers
create_exception_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["inventory"])
app.include_router(reservations.router, prefix="/api/v1/reservations", tags=["reservations"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["locations"])


@app.get(
    "/",
    summary="Service Information",
    description="""
Get basic information about the Inventory Management Service.

This is the root endpoint that provides:
- Service name
- Current version
- Database status (if connected)

Useful for quick service identification and version checking.
    """,
    response_description="Service information",
    responses={
        200: {
            "description": "Service information",
            "content": {
                "application/json": {
                    "example": {
                        "service": "inventory-management-service",
                        "version": "0.1.0",
                        "database": "connected",
                    }
                }
            },
        }
    },
    tags=["service-info"],
)
async def root() -> dict[str, str]:
    """Root endpoint."""
    info = {
        "service": settings.app_name,
        "version": settings.app_version,
    }

    # Add database status if configured
    if settings.database_url:
        info["database"] = "connected"
    else:
        info["database"] = "not configured"

    return info


@app.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="""
Export Prometheus metrics for monitoring and observability.

This endpoint provides metrics in Prometheus format for:
- HTTP request counts and durations
- Inventory operation metrics
- Database connection pool metrics
- Reservation statistics
- Low stock alerts
- Error rates and types

Used by Prometheus server for scraping metrics data.
    """,
    response_description="Prometheus metrics in text format", 
    include_in_schema=False,  # Hide from OpenAPI docs
    tags=["monitoring"],
)
async def metrics() -> Response:
    """Export Prometheus metrics."""
    metrics_data = generate_latest(service_registry)
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
    )