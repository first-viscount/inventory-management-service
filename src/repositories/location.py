"""Repository for location operations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update

from src.core.logging import get_logger
from src.models.inventory import Location, LocationType
from src.repositories.base import BaseRepository

logger = get_logger(__name__)


class LocationRepository(BaseRepository[Location]):
    """Repository for location operations."""

    async def create(self, **kwargs: Any) -> Location:
        """Create a new location."""
        location = Location(**kwargs)
        self.session.add(location)
        await self.session.flush()
        return location

    async def get(self, id: uuid.UUID) -> Location | None:
        """Get location by ID."""
        stmt = select(Location).where(Location.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Location | None:
        """Get location by name."""
        stmt = select(Location).where(Location.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, id: uuid.UUID, **kwargs: Any) -> Location | None:
        """Update location."""
        stmt = (
            update(Location)
            .where(Location.id == id)
            .values(**kwargs)
            .returning(Location)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete location (soft delete by setting active=False)."""
        location = await self.get(id)
        if location:
            location.active = False
            logger.info(
                "Location deactivated",
                location_id=str(location.id),
                name=location.name,
            )
            return True
        return False

    async def list(self, **filters: Any) -> list[Location]:
        """List locations with optional filters."""
        stmt = select(Location)
        
        # Apply filters
        if location_type := filters.get("type"):
            stmt = stmt.where(Location.type == location_type)
        
        # Only show active locations by default
        if filters.get("include_inactive", False) is False:
            stmt = stmt.where(Location.active == True)
        
        # Order by name
        stmt = stmt.order_by(Location.name)
        
        # Pagination
        if limit := filters.get("limit"):
            stmt = stmt.limit(limit)
        if offset := filters.get("offset"):
            stmt = stmt.offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_locations(self) -> list[Location]:
        """Get all active locations."""
        stmt = select(Location).where(Location.active == True).order_by(Location.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(self, location_type: LocationType) -> list[Location]:
        """Get all locations of a specific type."""
        stmt = (
            select(Location)
            .where(Location.type == location_type)
            .where(Location.active == True)
            .order_by(Location.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())