"""Reservation management API routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.inventory import ReservationResponse
from src.core.database import get_db
from src.core.exceptions import NotFoundError
from src.core.logging import get_logger
from src.models.inventory import ReservationStatus
from src.repositories.reservation import ReservationRepository

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[ReservationResponse],
    summary="List reservations",
    description="""
List reservations with optional filtering.

Can filter by:
- Order ID (get all reservations for an order)
- Product ID (get all reservations for a product)
- Status (active, expired, released, completed)

Results are ordered by creation time (newest first).
    """,
    responses={
        200: {"description": "Reservations retrieved successfully"},
    },
)
async def list_reservations(
    order_id: uuid.UUID | None = Query(None, description="Filter by order ID"),
    product_id: uuid.UUID | None = Query(None, description="Filter by product ID"),
    status: ReservationStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of reservations to return"),
    offset: int = Query(0, ge=0, description="Number of reservations to skip"),
    db: AsyncSession = Depends(get_db),
) -> list[ReservationResponse]:
    """List reservations with optional filters."""
    reservation_repo = ReservationRepository(db)
    
    filters = {"limit": limit, "offset": offset}
    if order_id:
        filters["order_id"] = order_id
    if product_id:
        filters["product_id"] = product_id
    if status:
        filters["status"] = status
    
    reservations = await reservation_repo.list(**filters)
    
    response = []
    for reservation in reservations:
        response.append(
            ReservationResponse(
                id=reservation.id,
                product_id=reservation.product_id,
                order_id=reservation.order_id,
                quantity=reservation.quantity,
                expires_at=reservation.expires_at,
                status=reservation.status,
                created_at=reservation.created_at,
                updated_at=reservation.updated_at,
            )
        )
    
    logger.info(
        "Reservations listed",
        count=len(response),
        order_id=str(order_id) if order_id else None,
        product_id=str(product_id) if product_id else None,
        status=status.value if status else None,
    )
    
    return response


@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
    summary="Get reservation details",
    description="""
Get detailed information about a specific reservation.

Returns reservation status, quantities, expiration time, and associated order/product IDs.
    """,
    responses={
        200: {"description": "Reservation details retrieved successfully"},
        404: {"description": "Reservation not found"},
    },
)
async def get_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    """Get reservation by ID."""
    reservation_repo = ReservationRepository(db)
    
    reservation = await reservation_repo.get(reservation_id)
    if not reservation:
        raise NotFoundError(f"Reservation {reservation_id} not found")
    
    return ReservationResponse(
        id=reservation.id,
        product_id=reservation.product_id,
        order_id=reservation.order_id,
        quantity=reservation.quantity,
        expires_at=reservation.expires_at,
        status=reservation.status,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at,
    )


@router.post(
    "/{reservation_id}/complete",
    response_model=ReservationResponse,
    summary="Mark reservation as completed",
    description="""
Mark a reservation as completed (inventory consumed).

This is typically called when an order is fulfilled and the reserved
inventory has been physically consumed/shipped.

This does NOT release inventory back to available - the inventory
has been consumed and the reserved quantity should be deducted
from the total stock.
    """,
    responses={
        200: {"description": "Reservation marked as completed"},
        404: {"description": "Reservation not found"},
        409: {"description": "Reservation cannot be completed (wrong status)"},
    },
)
async def complete_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    """Mark reservation as completed."""
    reservation_repo = ReservationRepository(db)
    
    try:
        success = await reservation_repo.mark_as_completed(reservation_id)
        if not success:
            raise NotFoundError(f"Reservation {reservation_id} not found or cannot be completed")
        
        # Get updated reservation
        reservation = await reservation_repo.get(reservation_id)
        if not reservation:
            raise NotFoundError(f"Reservation {reservation_id} not found")
        
        await db.commit()
        
        logger.info(
            "Reservation completed",
            reservation_id=str(reservation_id),
            order_id=str(reservation.order_id),
            product_id=str(reservation.product_id),
        )
        
        return ReservationResponse(
            id=reservation.id,
            product_id=reservation.product_id,
            order_id=reservation.order_id,
            quantity=reservation.quantity,
            expires_at=reservation.expires_at,
            status=reservation.status,
            created_at=reservation.created_at,
            updated_at=reservation.updated_at,
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, NotFoundError):
            raise
        
        logger.error(
            "Failed to complete reservation",
            reservation_id=str(reservation_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete reservation",
        )


@router.post(
    "/{reservation_id}/release",
    response_model=ReservationResponse,
    summary="Release reservation",
    description="""
Release a reservation and return inventory to available stock.

This is typically called when:
- An order is cancelled
- A reservation expires
- Manual intervention is needed

The reserved inventory will be moved back to available stock.
    """,
    responses={
        200: {"description": "Reservation released"},
        404: {"description": "Reservation not found"},
        409: {"description": "Reservation cannot be released (wrong status)"},
    },
)
async def release_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    """Release a reservation."""
    from src.repositories.inventory import InventoryRepository
    
    reservation_repo = ReservationRepository(db)
    inventory_repo = InventoryRepository(db)
    
    try:
        # Get reservation details first
        reservation = await reservation_repo.get(reservation_id)
        if not reservation or reservation.status != ReservationStatus.ACTIVE:
            raise NotFoundError(
                f"Active reservation {reservation_id} not found or cannot be released"
            )
        
        # Release inventory back to available stock
        success = await inventory_repo.release_inventory(
            product_id=reservation.product_id,
            location_id=reservation.inventory.location_id,
            quantity=reservation.quantity,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to release inventory - insufficient reserved stock",
            )
        
        # Mark reservation as released
        await reservation_repo.release_reservation(reservation_id)
        
        # Get updated reservation
        await db.refresh(reservation)
        
        await db.commit()
        
        logger.info(
            "Reservation released",
            reservation_id=str(reservation_id),
            order_id=str(reservation.order_id),
            product_id=str(reservation.product_id),
            quantity=reservation.quantity,
        )
        
        return ReservationResponse(
            id=reservation.id,
            product_id=reservation.product_id,
            order_id=reservation.order_id,
            quantity=reservation.quantity,
            expires_at=reservation.expires_at,
            status=reservation.status,
            created_at=reservation.created_at,
            updated_at=reservation.updated_at,
        )
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, (NotFoundError, HTTPException)):
            raise
        
        logger.error(
            "Failed to release reservation",
            reservation_id=str(reservation_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release reservation",
        )


@router.get(
    "/expired",
    response_model=list[ReservationResponse],
    summary="Get expired reservations",
    description="""
Get reservations that have expired but are still marked as active.

These reservations need to be processed to:
1. Release the reserved inventory back to available stock
2. Mark the reservation as expired
3. Optionally notify the order management system

This endpoint is typically called by background jobs for cleanup.
    """,
    responses={
        200: {"description": "Expired reservations retrieved successfully"},
    },
)
async def get_expired_reservations(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of expired reservations"),
    db: AsyncSession = Depends(get_db),
) -> list[ReservationResponse]:
    """Get expired reservations."""
    reservation_repo = ReservationRepository(db)
    
    expired_reservations = await reservation_repo.get_expired_reservations(limit=limit)
    
    response = []
    for reservation in expired_reservations:
        response.append(
            ReservationResponse(
                id=reservation.id,
                product_id=reservation.product_id,
                order_id=reservation.order_id,
                quantity=reservation.quantity,
                expires_at=reservation.expires_at,
                status=reservation.status,
                created_at=reservation.created_at,
                updated_at=reservation.updated_at,
            )
        )
    
    logger.info(
        "Expired reservations retrieved",
        count=len(response),
        limit=limit,
    )
    
    return response