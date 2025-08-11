"""Inventory management API routes."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.inventory import (
    AdjustInventoryRequest,
    CreateInventoryRequest,
    CreateLocationRequest,
    InventoryOperationResponse,
    InventoryResponse,
    InventoryStatsResponse,
    LocationResponse,
    LowStockItem,
    ReleaseInventoryRequest,
    ReservationResponse,
    ReserveInventoryRequest,
    UpdateInventoryRequest,
    UpdateLocationRequest,
)
from src.core.database import get_db
from src.core.exceptions import BadRequestError, ConflictError, InsufficientStockError, NotFoundError
from src.core.logging import get_logger
from src.models.inventory import AdjustmentType, LocationType, Reservation, ReservationStatus
from src.repositories.inventory import InventoryRepository
from src.repositories.location import LocationRepository
from src.repositories.reservation import ReservationRepository

logger = get_logger(__name__)

router = APIRouter()


# Inventory endpoints
@router.get(
    "/{product_id}",
    response_model=InventoryStatsResponse,
    summary="Get inventory for a product",
    description="""
Get current inventory status for a product across all locations.

Returns:
- Total available and reserved quantities
- Per-location inventory breakdown
- Low stock indicators
    """,
    responses={
        200: {"description": "Inventory information retrieved successfully"},
        404: {"description": "Product inventory not found"},
    },
)
async def get_inventory(
    product_id: uuid.UUID,
    location_id: uuid.UUID | None = Query(None, description="Filter by specific location"),
    db: AsyncSession = Depends(get_db),
) -> InventoryStatsResponse:
    """Get inventory for a product."""
    inventory_repo = InventoryRepository(db)
    
    if location_id:
        # Get specific location inventory
        inventory = await inventory_repo.get_by_product_and_location(product_id, location_id)
        if not inventory:
            raise NotFoundError(f"Inventory not found for product {product_id} at location {location_id}")
        
        inventories = [inventory]
    else:
        # Get all locations for product
        inventories = await inventory_repo.get_by_product(product_id)
        if not inventories:
            raise NotFoundError(f"No inventory found for product {product_id}")
    
    # Calculate totals
    total_available = sum(inv.quantity_available for inv in inventories)
    total_reserved = sum(inv.quantity_reserved for inv in inventories)
    
    # Convert to response models
    inventory_responses = []
    for inv in inventories:
        inventory_responses.append(
            InventoryResponse(
                id=inv.id,
                product_id=inv.product_id,
                location_id=inv.location_id,
                quantity_available=inv.quantity_available,
                quantity_reserved=inv.quantity_reserved,
                total_quantity=inv.total_quantity,
                reorder_point=inv.reorder_point,
                reorder_quantity=inv.reorder_quantity,
                is_low_stock=inv.is_low_stock,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
                location=LocationResponse(
                    id=inv.location.id,
                    name=inv.location.name,
                    address=inv.location.address,
                    type=inv.location.type,
                    active=inv.location.active,
                    created_at=inv.location.created_at,
                    updated_at=inv.location.updated_at,
                ),
            )
        )
    
    return InventoryStatsResponse(
        product_id=product_id,
        total_available=total_available,
        total_reserved=total_reserved,
        locations=inventory_responses,
    )


@router.post(
    "/reserve",
    response_model=InventoryOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve inventory",
    description="""
Reserve inventory for an order.

The reservation will:
- Check if sufficient stock is available
- Atomically move quantity from available to reserved
- Create a reservation record with expiration
- Return reservation details

Reservations expire automatically and should be confirmed or released.
    """,
    responses={
        201: {"description": "Inventory reserved successfully"},
        409: {"description": "Insufficient stock available"},
        404: {"description": "Product or location not found"},
    },
)
async def reserve_inventory(
    request: ReserveInventoryRequest,
    db: AsyncSession = Depends(get_db),
) -> InventoryOperationResponse:
    """Reserve inventory for an order."""
    inventory_repo = InventoryRepository(db)
    reservation_repo = ReservationRepository(db)
    
    try:
        # Check if inventory exists
        inventory = await inventory_repo.get_by_product_and_location(
            request.product_id, request.location_id
        )
        if not inventory:
            raise NotFoundError(
                f"Inventory not found for product {request.product_id} at location {request.location_id}"
            )
        
        # Reserve inventory (atomic operation)
        success = await inventory_repo.reserve_inventory(
            request.product_id, request.location_id, request.quantity
        )
        
        if not success:
            raise InsufficientStockError(
                f"Insufficient stock available. Requested: {request.quantity}, "
                f"Available: {inventory.quantity_available}"
            )
        
        # Create reservation record
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=request.expires_minutes)
        reservation = await reservation_repo.create(
            inventory_id=inventory.id,
            product_id=request.product_id,
            order_id=request.order_id,
            quantity=request.quantity,
            expires_at=expires_at,
            status=ReservationStatus.ACTIVE,
        )
        
        # Refresh inventory data
        await db.refresh(inventory)
        
        # Build response
        inventory_response = InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            location_id=inventory.location_id,
            quantity_available=inventory.quantity_available,
            quantity_reserved=inventory.quantity_reserved,
            total_quantity=inventory.total_quantity,
            reorder_point=inventory.reorder_point,
            reorder_quantity=inventory.reorder_quantity,
            is_low_stock=inventory.is_low_stock,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
            location=LocationResponse(
                id=inventory.location.id,
                name=inventory.location.name,
                address=inventory.location.address,
                type=inventory.location.type,
                active=inventory.location.active,
                created_at=inventory.location.created_at,
                updated_at=inventory.location.updated_at,
            ),
        )
        
        reservation_response = ReservationResponse(
            id=reservation.id,
            product_id=reservation.product_id,
            order_id=reservation.order_id,
            quantity=reservation.quantity,
            expires_at=reservation.expires_at,
            status=reservation.status,
            created_at=reservation.created_at,
            updated_at=reservation.updated_at,
        )
        
        await db.commit()
        
        logger.info(
            "Inventory reserved successfully",
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            order_id=str(request.order_id),
            quantity=request.quantity,
            reservation_id=str(reservation.id),
        )
        
        return InventoryOperationResponse(
            success=True,
            message=f"Reserved {request.quantity} units",
            inventory=inventory_response,
            reservation=reservation_response,
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, (NotFoundError, InsufficientStockError)):
            raise
        
        logger.error(
            "Failed to reserve inventory",
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            order_id=str(request.order_id),
            quantity=request.quantity,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reserve inventory",
        )


@router.post(
    "/release",
    response_model=InventoryOperationResponse,
    summary="Release inventory reservation",
    description="""
Release reserved inventory back to available stock.

This operation:
- Finds the active reservation for the order
- Atomically moves quantity from reserved to available
- Marks the reservation as released

Used when orders are cancelled or when reservations expire.
    """,
    responses={
        200: {"description": "Inventory released successfully"},
        404: {"description": "Reservation not found or already released"},
        409: {"description": "Invalid reservation state"},
    },
)
async def release_inventory(
    request: ReleaseInventoryRequest,
    db: AsyncSession = Depends(get_db),
) -> InventoryOperationResponse:
    """Release reserved inventory."""
    inventory_repo = InventoryRepository(db)
    reservation_repo = ReservationRepository(db)
    
    try:
        # Find active reservations for this order
        reservations = await reservation_repo.get_active_by_order(request.order_id)
        
        # Find matching reservation
        matching_reservation = None
        for res in reservations:
            if (
                res.product_id == request.product_id
                and res.quantity == request.quantity
                and res.inventory.location_id == request.location_id
            ):
                matching_reservation = res
                break
        
        if not matching_reservation:
            raise NotFoundError(
                f"No matching active reservation found for order {request.order_id}"
            )
        
        # Release inventory (atomic operation)
        success = await inventory_repo.release_inventory(
            request.product_id, request.location_id, request.quantity
        )
        
        if not success:
            raise ConflictError("Failed to release inventory - insufficient reserved stock")
        
        # Mark reservation as released
        await reservation_repo.release_reservation(matching_reservation.id)
        
        # Get updated inventory
        inventory = await inventory_repo.get_by_product_and_location(
            request.product_id, request.location_id
        )
        
        # Build response
        inventory_response = InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            location_id=inventory.location_id,
            quantity_available=inventory.quantity_available,
            quantity_reserved=inventory.quantity_reserved,
            total_quantity=inventory.total_quantity,
            reorder_point=inventory.reorder_point,
            reorder_quantity=inventory.reorder_quantity,
            is_low_stock=inventory.is_low_stock,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
            location=LocationResponse(
                id=inventory.location.id,
                name=inventory.location.name,
                address=inventory.location.address,
                type=inventory.location.type,
                active=inventory.location.active,
                created_at=inventory.location.created_at,
                updated_at=inventory.location.updated_at,
            ),
        )
        
        await db.commit()
        
        logger.info(
            "Inventory released successfully",
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            order_id=str(request.order_id),
            quantity=request.quantity,
            reservation_id=str(matching_reservation.id),
        )
        
        return InventoryOperationResponse(
            success=True,
            message=f"Released {request.quantity} units",
            inventory=inventory_response,
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, (NotFoundError, ConflictError)):
            raise
        
        logger.error(
            "Failed to release inventory",
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            order_id=str(request.order_id),
            quantity=request.quantity,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release inventory",
        )


@router.post(
    "/adjust",
    response_model=InventoryOperationResponse,
    summary="Adjust inventory levels",
    description="""
Manually adjust inventory levels.

This operation:
- Adjusts available inventory (positive to add, negative to remove)
- Creates an adjustment record for audit trail
- Prevents negative inventory levels
- Supports various adjustment types (restock, damage, correction, etc.)

Used for receiving stock, recording damage, manual corrections, etc.
    """,
    responses={
        200: {"description": "Inventory adjusted successfully"},
        400: {"description": "Invalid adjustment (would result in negative inventory)"},
        404: {"description": "Product or location not found"},
    },
)
async def adjust_inventory(
    request: AdjustInventoryRequest,
    db: AsyncSession = Depends(get_db),
) -> InventoryOperationResponse:
    """Adjust inventory levels."""
    inventory_repo = InventoryRepository(db)
    
    try:
        # Check if inventory exists
        inventory = await inventory_repo.get_by_product_and_location(
            request.product_id, request.location_id
        )
        if not inventory:
            raise NotFoundError(
                f"Inventory not found for product {request.product_id} at location {request.location_id}"
            )
        
        # Perform adjustment
        success = await inventory_repo.adjust_inventory(
            product_id=request.product_id,
            location_id=request.location_id,
            quantity_change=request.quantity_change,
            adjustment_type=request.adjustment_type,
            reason=request.reason,
            created_by=request.created_by,
        )
        
        if not success:
            if request.quantity_change < 0:
                raise BadRequestError(
                    f"Adjustment would result in negative inventory. "
                    f"Current: {inventory.quantity_available}, Adjustment: {request.quantity_change}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to adjust inventory",
                )
        
        # Get updated inventory
        await db.refresh(inventory)
        
        # Build response
        inventory_response = InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            location_id=inventory.location_id,
            quantity_available=inventory.quantity_available,
            quantity_reserved=inventory.quantity_reserved,
            total_quantity=inventory.total_quantity,
            reorder_point=inventory.reorder_point,
            reorder_quantity=inventory.reorder_quantity,
            is_low_stock=inventory.is_low_stock,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
            location=LocationResponse(
                id=inventory.location.id,
                name=inventory.location.name,
                address=inventory.location.address,
                type=inventory.location.type,
                active=inventory.location.active,
                created_at=inventory.location.created_at,
                updated_at=inventory.location.updated_at,
            ),
        )
        
        await db.commit()
        
        logger.info(
            "Inventory adjusted successfully",
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            adjustment=request.quantity_change,
            type=request.adjustment_type.value,
            new_quantity=inventory.quantity_available,
            created_by=request.created_by,
        )
        
        operation = "Added" if request.quantity_change > 0 else "Removed"
        return InventoryOperationResponse(
            success=True,
            message=f"{operation} {abs(request.quantity_change)} units ({request.adjustment_type.value})",
            inventory=inventory_response,
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, (NotFoundError, BadRequestError)):
            raise
        
        logger.error(
            "Failed to adjust inventory",
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            adjustment=request.quantity_change,
            type=request.adjustment_type.value,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to adjust inventory",
        )


@router.get(
    "/low-stock",
    response_model=list[LowStockItem],
    summary="Get low stock items",
    description="""
Get items that are below their reorder point.

Returns a list of inventory items where available quantity is at or below
the reorder point, sorted by shortage amount (most critical first).

Useful for generating purchase orders and stock alerts.
    """,
    responses={
        200: {"description": "Low stock items retrieved successfully"},
    },
)
async def get_low_stock(
    location_id: uuid.UUID | None = Query(None, description="Filter by location"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db),
) -> list[LowStockItem]:
    """Get items with low stock."""
    inventory_repo = InventoryRepository(db)
    
    low_stock_items = await inventory_repo.get_low_stock_items(
        location_id=location_id, limit=limit
    )
    
    response_items = []
    for item in low_stock_items:
        shortage = item.reorder_point - item.quantity_available
        
        response_items.append(
            LowStockItem(
                product_id=item.product_id,
                location=LocationResponse(
                    id=item.location.id,
                    name=item.location.name,
                    address=item.location.address,
                    type=item.location.type,
                    active=item.location.active,
                    created_at=item.location.created_at,
                    updated_at=item.location.updated_at,
                ),
                quantity_available=item.quantity_available,
                reorder_point=item.reorder_point,
                reorder_quantity=item.reorder_quantity,
                shortage=shortage,
            )
        )
    
    # Sort by shortage (most critical first)
    response_items.sort(key=lambda x: x.shortage, reverse=True)
    
    logger.info(
        "Low stock items retrieved",
        count=len(response_items),
        location_id=str(location_id) if location_id else "all",
        limit=limit,
    )
    
    return response_items


# Administrative endpoints
@router.post(
    "",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create inventory record",
    description="""
Create a new inventory record for a product at a location.

This is typically used when adding a new product to a location
or when setting up initial inventory levels.
    """,
    responses={
        201: {"description": "Inventory record created successfully"},
        409: {"description": "Inventory already exists for this product-location combination"},
        404: {"description": "Location not found"},
    },
)
async def create_inventory(
    request: CreateInventoryRequest,
    db: AsyncSession = Depends(get_db),
) -> InventoryResponse:
    """Create a new inventory record."""
    inventory_repo = InventoryRepository(db)
    location_repo = LocationRepository(db)
    
    try:
        # Check if location exists
        location = await location_repo.get(request.location_id)
        if not location:
            raise NotFoundError(f"Location {request.location_id} not found")
        
        # Check if inventory already exists
        existing = await inventory_repo.get_by_product_and_location(
            request.product_id, request.location_id
        )
        if existing:
            raise ConflictError(
                f"Inventory already exists for product {request.product_id} at location {request.location_id}"
            )
        
        # Create inventory
        inventory = await inventory_repo.create(
            product_id=request.product_id,
            location_id=request.location_id,
            quantity_available=request.quantity_available,
            quantity_reserved=0,
            reorder_point=request.reorder_point,
            reorder_quantity=request.reorder_quantity,
        )
        
        await db.commit()
        
        logger.info(
            "Inventory record created",
            inventory_id=str(inventory.id),
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            quantity=request.quantity_available,
        )
        
        return InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            location_id=inventory.location_id,
            quantity_available=inventory.quantity_available,
            quantity_reserved=inventory.quantity_reserved,
            total_quantity=inventory.total_quantity,
            reorder_point=inventory.reorder_point,
            reorder_quantity=inventory.reorder_quantity,
            is_low_stock=inventory.is_low_stock,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
            location=LocationResponse(
                id=location.id,
                name=location.name,
                address=location.address,
                type=location.type,
                active=location.active,
                created_at=location.created_at,
                updated_at=location.updated_at,
            ),
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, (NotFoundError, ConflictError)):
            raise
        
        logger.error(
            "Failed to create inventory record",
            product_id=str(request.product_id),
            location_id=str(request.location_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create inventory record",
        )