"""Repository for inventory operations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.models.inventory import (
    AdjustmentType,
    Inventory,
    InventoryAdjustment,
)
from src.repositories.base import BaseRepository

logger = get_logger(__name__)


class InventoryRepository(BaseRepository[Inventory]):
    """Repository for inventory operations."""

    async def create(self, **kwargs: Any) -> Inventory:
        """Create a new inventory record."""
        inventory = Inventory(**kwargs)
        self.session.add(inventory)
        await self.session.flush()
        await self.session.refresh(inventory, ["location"])
        return inventory

    async def get(self, id: uuid.UUID) -> Inventory | None:
        """Get inventory by ID."""
        stmt = (
            select(Inventory)
            .options(selectinload(Inventory.location))
            .where(Inventory.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_product_and_location(
        self, product_id: uuid.UUID, location_id: uuid.UUID,
    ) -> Inventory | None:
        """Get inventory by product and location."""
        stmt = (
            select(Inventory)
            .options(selectinload(Inventory.location))
            .where(
                and_(
                    Inventory.product_id == product_id,
                    Inventory.location_id == location_id,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_product(self, product_id: uuid.UUID) -> list[Inventory]:
        """Get all inventory records for a product across all locations."""
        stmt = (
            select(Inventory)
            .options(selectinload(Inventory.location))
            .where(Inventory.product_id == product_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, **kwargs: Any) -> Inventory | None:
        """Update inventory record."""
        stmt = (
            update(Inventory)
            .where(Inventory.id == id)
            .values(**kwargs)
            .returning(Inventory)
        )
        result = await self.session.execute(stmt)
        inventory = result.scalar_one_or_none()
        if inventory:
            await self.session.refresh(inventory, ["location"])
        return inventory

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete inventory record."""
        inventory = await self.get(id)
        if inventory:
            await self.session.delete(inventory)
            return True
        return False

    async def list(self, **filters: Any) -> list[Inventory]:
        """List inventory records with optional filters."""
        stmt = select(Inventory).options(selectinload(Inventory.location))
        
        # Apply filters
        if location_id := filters.get("location_id"):
            stmt = stmt.where(Inventory.location_id == location_id)
        if product_ids := filters.get("product_ids"):
            stmt = stmt.where(Inventory.product_id.in_(product_ids))
        
        # Pagination
        if limit := filters.get("limit"):
            stmt = stmt.limit(limit)
        if offset := filters.get("offset"):
            stmt = stmt.offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_low_stock_items(
        self, location_id: uuid.UUID | None = None, limit: int = 100,
    ) -> list[Inventory]:
        """Get items with low stock (below reorder point)."""
        stmt = (
            select(Inventory)
            .options(selectinload(Inventory.location))
            .where(Inventory.quantity_available <= Inventory.reorder_point)
        )
        
        if location_id:
            stmt = stmt.where(Inventory.location_id == location_id)
        
        stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reserve_inventory(
        self, product_id: uuid.UUID, location_id: uuid.UUID, quantity: int,
    ) -> bool:
        """Reserve inventory quantity (atomic operation)."""
        try:
            # Get current inventory with row lock
            stmt = (
                select(Inventory)
                .where(
                    and_(
                        Inventory.product_id == product_id,
                        Inventory.location_id == location_id,
                    ),
                )
                .with_for_update()
            )
            result = await self.session.execute(stmt)
            inventory = result.scalar_one_or_none()
            
            if not inventory or inventory.quantity_available < quantity:
                logger.warning(
                    "Insufficient inventory for reservation",
                    product_id=str(product_id),
                    location_id=str(location_id),
                    requested=quantity,
                    available=inventory.quantity_available if inventory else 0,
                )
                return False
            
            # Update quantities atomically
            inventory.quantity_available -= quantity
            inventory.quantity_reserved += quantity
            
            logger.info(
                "Inventory reserved successfully",
                product_id=str(product_id),
                location_id=str(location_id),
                quantity=quantity,
                new_available=inventory.quantity_available,
                new_reserved=inventory.quantity_reserved,
            )
            return True
        
        except Exception as e:
            logger.exception(
                "Failed to reserve inventory",
                product_id=str(product_id),
                location_id=str(location_id),
                quantity=quantity,
            )
            return False

    async def release_inventory(
        self, product_id: uuid.UUID, location_id: uuid.UUID, quantity: int,
    ) -> bool:
        """Release reserved inventory quantity (atomic operation)."""
        try:
            # Get current inventory with row lock
            stmt = (
                select(Inventory)
                .where(
                    and_(
                        Inventory.product_id == product_id,
                        Inventory.location_id == location_id,
                    ),
                )
                .with_for_update()
            )
            result = await self.session.execute(stmt)
            inventory = result.scalar_one_or_none()
            
            if not inventory or inventory.quantity_reserved < quantity:
                logger.warning(
                    "Insufficient reserved inventory to release",
                    product_id=str(product_id),
                    location_id=str(location_id),
                    requested=quantity,
                    reserved=inventory.quantity_reserved if inventory else 0,
                )
                return False
            
            # Update quantities atomically
            inventory.quantity_available += quantity
            inventory.quantity_reserved -= quantity
            
            logger.info(
                "Inventory released successfully",
                product_id=str(product_id),
                location_id=str(location_id),
                quantity=quantity,
                new_available=inventory.quantity_available,
                new_reserved=inventory.quantity_reserved,
            )
            return True
        
        except Exception as e:
            logger.exception(
                "Failed to release inventory",
                product_id=str(product_id),
                location_id=str(location_id),
                quantity=quantity,
            )
            return False

    async def adjust_inventory(
        self,
        product_id: uuid.UUID,
        location_id: uuid.UUID,
        quantity_change: int,
        adjustment_type: AdjustmentType,
        reason: str | None = None,
        created_by: str = "system",
    ) -> bool:
        """Adjust inventory quantity and create adjustment record."""
        try:
            # Get current inventory with row lock
            stmt = (
                select(Inventory)
                .where(
                    and_(
                        Inventory.product_id == product_id,
                        Inventory.location_id == location_id,
                    ),
                )
                .with_for_update()
            )
            result = await self.session.execute(stmt)
            inventory = result.scalar_one_or_none()
            
            if not inventory:
                logger.error(
                    "Inventory record not found for adjustment",
                    product_id=str(product_id),
                    location_id=str(location_id),
                )
                return False
            
            # Prevent negative inventory
            new_quantity = inventory.quantity_available + quantity_change
            if new_quantity < 0:
                logger.warning(
                    "Adjustment would result in negative inventory",
                    product_id=str(product_id),
                    location_id=str(location_id),
                    current=inventory.quantity_available,
                    adjustment=quantity_change,
                    would_be=new_quantity,
                )
                return False
            
            # Update inventory
            inventory.quantity_available = new_quantity
            
            # Create adjustment record
            adjustment = InventoryAdjustment(
                inventory_id=inventory.id,
                product_id=product_id,
                adjustment_type=adjustment_type,
                quantity=quantity_change,
                reason=reason,
                created_by=created_by,
            )
            self.session.add(adjustment)
            
            logger.info(
                "Inventory adjusted successfully",
                product_id=str(product_id),
                location_id=str(location_id),
                adjustment=quantity_change,
                type=adjustment_type.value,
                new_quantity=inventory.quantity_available,
                created_by=created_by,
            )
            return True
        
        except Exception as e:
            logger.exception(
                "Failed to adjust inventory",
                product_id=str(product_id),
                location_id=str(location_id),
                adjustment=quantity_change,
                type=adjustment_type.value,
            )
            return False