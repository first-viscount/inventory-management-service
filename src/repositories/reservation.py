"""Repository for reservation operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.models.inventory import Reservation, ReservationStatus
from src.repositories.base import BaseRepository

logger = get_logger(__name__)


class ReservationRepository(BaseRepository[Reservation]):
    """Repository for reservation operations."""

    async def create(self, **kwargs: Any) -> Reservation:
        """Create a new reservation."""
        reservation = Reservation(**kwargs)
        self.session.add(reservation)
        await self.session.flush()
        await self.session.refresh(reservation, ["inventory"])
        return reservation

    async def get(self, id: uuid.UUID) -> Reservation | None:
        """Get reservation by ID."""
        stmt = (
            select(Reservation)
            .options(selectinload(Reservation.inventory))
            .where(Reservation.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order(self, order_id: uuid.UUID) -> list[Reservation]:
        """Get all reservations for an order."""
        stmt = (
            select(Reservation)
            .options(selectinload(Reservation.inventory))
            .where(Reservation.order_id == order_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_order(self, order_id: uuid.UUID) -> list[Reservation]:
        """Get active reservations for an order."""
        stmt = (
            select(Reservation)
            .options(selectinload(Reservation.inventory))
            .where(
                and_(
                    Reservation.order_id == order_id,
                    Reservation.status == ReservationStatus.ACTIVE,
                )
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, **kwargs: Any) -> Reservation | None:
        """Update reservation."""
        stmt = (
            update(Reservation)
            .where(Reservation.id == id)
            .values(**kwargs)
            .returning(Reservation)
        )
        result = await self.session.execute(stmt)
        reservation = result.scalar_one_or_none()
        if reservation:
            await self.session.refresh(reservation, ["inventory"])
        return reservation

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete reservation."""
        reservation = await self.get(id)
        if reservation:
            await self.session.delete(reservation)
            return True
        return False

    async def list(self, **filters: Any) -> list[Reservation]:
        """List reservations with optional filters."""
        stmt = select(Reservation).options(selectinload(Reservation.inventory))
        
        # Apply filters
        if order_id := filters.get("order_id"):
            stmt = stmt.where(Reservation.order_id == order_id)
        if product_id := filters.get("product_id"):
            stmt = stmt.where(Reservation.product_id == product_id)
        if status := filters.get("status"):
            stmt = stmt.where(Reservation.status == status)
        
        # Order by creation time (newest first)
        stmt = stmt.order_by(Reservation.created_at.desc())
        
        # Pagination
        if limit := filters.get("limit"):
            stmt = stmt.limit(limit)
        if offset := filters.get("offset"):
            stmt = stmt.offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_reservations(self, limit: int = 100) -> list[Reservation]:
        """Get expired reservations that need to be processed."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Reservation)
            .options(selectinload(Reservation.inventory))
            .where(
                and_(
                    Reservation.status == ReservationStatus.ACTIVE,
                    Reservation.expires_at <= now,
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_completed(self, reservation_id: uuid.UUID) -> bool:
        """Mark a reservation as completed (inventory consumed)."""
        try:
            reservation = await self.get(reservation_id)
            if not reservation or reservation.status != ReservationStatus.ACTIVE:
                logger.warning(
                    "Cannot complete reservation",
                    reservation_id=str(reservation_id),
                    current_status=reservation.status.value if reservation else "not_found",
                )
                return False
            
            reservation.status = ReservationStatus.COMPLETED
            
            logger.info(
                "Reservation marked as completed",
                reservation_id=str(reservation_id),
                order_id=str(reservation.order_id),
                product_id=str(reservation.product_id),
                quantity=reservation.quantity,
            )
            return True
        
        except Exception as e:
            logger.error(
                "Failed to mark reservation as completed",
                reservation_id=str(reservation_id),
                error=str(e),
            )
            return False

    async def mark_as_expired(self, reservation_id: uuid.UUID) -> bool:
        """Mark a reservation as expired."""
        try:
            reservation = await self.get(reservation_id)
            if not reservation or reservation.status != ReservationStatus.ACTIVE:
                logger.warning(
                    "Cannot expire reservation",
                    reservation_id=str(reservation_id),
                    current_status=reservation.status.value if reservation else "not_found",
                )
                return False
            
            reservation.status = ReservationStatus.EXPIRED
            
            logger.info(
                "Reservation marked as expired",
                reservation_id=str(reservation_id),
                order_id=str(reservation.order_id),
                product_id=str(reservation.product_id),
                quantity=reservation.quantity,
            )
            return True
        
        except Exception as e:
            logger.error(
                "Failed to mark reservation as expired",
                reservation_id=str(reservation_id),
                error=str(e),
            )
            return False

    async def release_reservation(self, reservation_id: uuid.UUID) -> bool:
        """Release a reservation (mark as released)."""
        try:
            reservation = await self.get(reservation_id)
            if not reservation or reservation.status != ReservationStatus.ACTIVE:
                logger.warning(
                    "Cannot release reservation",
                    reservation_id=str(reservation_id),
                    current_status=reservation.status.value if reservation else "not_found",
                )
                return False
            
            reservation.status = ReservationStatus.RELEASED
            
            logger.info(
                "Reservation released",
                reservation_id=str(reservation_id),
                order_id=str(reservation.order_id),
                product_id=str(reservation.product_id),
                quantity=reservation.quantity,
            )
            return True
        
        except Exception as e:
            logger.error(
                "Failed to release reservation",
                reservation_id=str(reservation_id),
                error=str(e),
            )
            return False