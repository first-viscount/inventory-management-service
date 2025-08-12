"""Location management API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.inventory import (
    CreateLocationRequest,
    LocationResponse,
    UpdateLocationRequest,
)
from src.core.database import get_db
from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger
from src.models.inventory import LocationType
from src.repositories.location import LocationRepository

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[LocationResponse],
    summary="List locations",
    description="""
List all locations with optional filtering.

Can filter by:
- Location type (warehouse, store, online, dropship)
- Active status

Results are ordered alphabetically by name.
    """,
    responses={
        200: {"description": "Locations retrieved successfully"},
    },
)
async def list_locations(
    type: LocationType | None = Query(None, description="Filter by location type"),
    include_inactive: bool = Query(False, description="Include inactive locations"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of locations to return"),
    offset: int = Query(0, ge=0, description="Number of locations to skip"),
    db: AsyncSession = Depends(get_db),
) -> list[LocationResponse]:
    """List locations with optional filters."""
    location_repo = LocationRepository(db)
    
    filters = {"limit": limit, "offset": offset, "include_inactive": include_inactive}
    if type:
        filters["type"] = type
    
    locations = await location_repo.list(**filters)
    
    response = []
    for location in locations:
        response.append(
            LocationResponse(
                id=location.id,
                name=location.name,
                address=location.address,
                type=location.type,
                active=location.active,
                created_at=location.created_at,
                updated_at=location.updated_at,
            ),
        )
    
    logger.info(
        "Locations listed",
        count=len(response),
        type=type.value if type else None,
        include_inactive=include_inactive,
    )
    
    return response


@router.get(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Get location details",
    description="""
Get detailed information about a specific location.

Returns location name, address, type, and active status.
    """,
    responses={
        200: {"description": "Location details retrieved successfully"},
        404: {"description": "Location not found"},
    },
)
async def get_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    """Get location by ID."""
    location_repo = LocationRepository(db)
    
    location = await location_repo.get(location_id)
    if not location:
        raise NotFoundError(f"Location {location_id} not found")
    
    return LocationResponse(
        id=location.id,
        name=location.name,
        address=location.address,
        type=location.type,
        active=location.active,
        created_at=location.created_at,
        updated_at=location.updated_at,
    )


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create location",
    description="""
Create a new inventory location.

Location names must be unique across the system.
Locations are created as active by default.

Types of locations:
- warehouse: Distribution centers, fulfillment centers
- store: Physical retail stores
- online: Online-only inventory (virtual locations)
- dropship: Supplier dropship locations
    """,
    responses={
        201: {"description": "Location created successfully"},
        409: {"description": "Location name already exists"},
    },
)
async def create_location(
    request: CreateLocationRequest,
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    """Create a new location."""
    location_repo = LocationRepository(db)
    
    try:
        # Check if location name already exists
        existing = await location_repo.get_by_name(request.name)
        if existing:
            raise ConflictError(f"Location with name '{request.name}' already exists")
        
        # Create location
        location = await location_repo.create(
            name=request.name,
            address=request.address,
            type=request.type,
        )
        
        await db.commit()
        
        logger.info(
            "Location created",
            location_id=str(location.id),
            name=location.name,
            type=location.type.value,
        )
        
        return LocationResponse(
            id=location.id,
            name=location.name,
            address=location.address,
            type=location.type,
            active=location.active,
            created_at=location.created_at,
            updated_at=location.updated_at,
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, ConflictError):
            raise
        
        logger.exception(
            "Failed to create location",
            name=request.name,
            type=request.type.value,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create location",
        )


@router.put(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Update location",
    description="""
Update location information.

Can update:
- Name (must remain unique)
- Address
- Type
- Active status

Only provided fields will be updated.
    """,
    responses={
        200: {"description": "Location updated successfully"},
        404: {"description": "Location not found"},
        409: {"description": "Location name already exists"},
    },
)
async def update_location(
    location_id: uuid.UUID,
    request: UpdateLocationRequest,
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    """Update location."""
    location_repo = LocationRepository(db)
    
    try:
        # Check if location exists
        location = await location_repo.get(location_id)
        if not location:
            raise NotFoundError(f"Location {location_id} not found")
        
        # Check for name conflicts if name is being updated
        if request.name and request.name != location.name:
            existing = await location_repo.get_by_name(request.name)
            if existing:
                raise ConflictError(f"Location with name '{request.name}' already exists")
        
        # Prepare update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.address is not None:
            update_data["address"] = request.address
        if request.type is not None:
            update_data["type"] = request.type
        if request.active is not None:
            update_data["active"] = request.active
        
        if not update_data:
            # No changes requested, return current location
            return LocationResponse(
                id=location.id,
                name=location.name,
                address=location.address,
                type=location.type,
                active=location.active,
                created_at=location.created_at,
                updated_at=location.updated_at,
            )
        
        # Update location
        updated_location = await location_repo.update(location_id, **update_data)
        if not updated_location:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update location",
            )
        
        await db.commit()
        
        logger.info(
            "Location updated",
            location_id=str(location_id),
            updates=update_data,
        )
        
        return LocationResponse(
            id=updated_location.id,
            name=updated_location.name,
            address=updated_location.address,
            type=updated_location.type,
            active=updated_location.active,
            created_at=updated_location.created_at,
            updated_at=updated_location.updated_at,
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, (NotFoundError, ConflictError, HTTPException)):
            raise
        
        logger.exception(
            "Failed to update location",
            location_id=str(location_id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update location",
        )


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate location",
    description="""
Deactivate a location (soft delete).

This marks the location as inactive rather than physically deleting it.
Inactive locations:
- Won't appear in default location lists
- Cannot have new inventory added
- Existing inventory remains accessible

Physical deletion is not supported to preserve audit trails and
prevent orphaned inventory records.
    """,
    responses={
        204: {"description": "Location deactivated successfully"},
        404: {"description": "Location not found"},
    },
)
async def deactivate_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate (soft delete) a location."""
    location_repo = LocationRepository(db)
    
    try:
        success = await location_repo.delete(location_id)
        if not success:
            raise NotFoundError(f"Location {location_id} not found")
        
        await db.commit()
        
        logger.info(
            "Location deactivated",
            location_id=str(location_id),
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, NotFoundError):
            raise
        
        logger.exception(
            "Failed to deactivate location",
            location_id=str(location_id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate location",
        )


@router.get(
    "/types/{location_type}",
    response_model=list[LocationResponse],
    summary="Get locations by type",
    description="""
Get all active locations of a specific type.

This is a convenience endpoint for getting locations by type
without needing to use query parameters.

Common use cases:
- Get all warehouses for distribution planning
- Get all stores for inventory allocation
- Get dropship locations for supplier management
    """,
    responses={
        200: {"description": "Locations retrieved successfully"},
    },
)
async def get_locations_by_type(
    location_type: LocationType,
    db: AsyncSession = Depends(get_db),
) -> list[LocationResponse]:
    """Get all locations of a specific type."""
    location_repo = LocationRepository(db)
    
    locations = await location_repo.get_by_type(location_type)
    
    response = []
    for location in locations:
        response.append(
            LocationResponse(
                id=location.id,
                name=location.name,
                address=location.address,
                type=location.type,
                active=location.active,
                created_at=location.created_at,
                updated_at=location.updated_at,
            ),
        )
    
    logger.info(
        "Locations by type retrieved",
        type=location_type.value,
        count=len(response),
    )
    
    return response