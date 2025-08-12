"""Background tasks for updating metrics."""

import asyncio

from sqlalchemy import func, select

from src.core.database import get_db_context
from src.core.logging import get_logger
from src.core.metrics import get_metrics_collector
from src.models.inventory import Inventory, Location, Reservation

logger = get_logger(__name__)


class BackgroundMetricsUpdater:
    """Background service to update metrics that require database queries."""

    def __init__(self, update_interval: int = 30) -> None:
        """Initialize the background metrics updater.
        
        Args:
            update_interval: Interval in seconds between metric updates
        """
        self.update_interval = update_interval
        self.metrics = get_metrics_collector()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background metrics update task."""
        if self._running:
            logger.warning("Background metrics updater is already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info("Background metrics updater started", interval=self.update_interval)

    async def stop(self) -> None:
        """Stop the background metrics update task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background metrics updater stopped")

    async def _update_loop(self) -> None:
        """Main update loop for background metrics."""
        while self._running:
            try:
                await self._update_inventory_metrics()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error updating background metrics")
                await asyncio.sleep(self.update_interval)

    async def _update_inventory_metrics(self) -> None:
        """Update inventory metrics."""
        try:
            async with get_db_context() as session:
                # Count total inventory records
                inventory_count_stmt = select(func.count(Inventory.id))
                inventory_result = await session.execute(inventory_count_stmt)
                total_inventory = inventory_result.scalar_one()
                
                # Count total locations
                location_count_stmt = select(func.count(Location.id))
                location_result = await session.execute(location_count_stmt)
                total_locations = location_result.scalar_one()
                
                # Count active reservations
                reservation_count_stmt = select(func.count(Reservation.id)).where(
                    Reservation.status == "active",
                )
                reservation_result = await session.execute(reservation_count_stmt)
                active_reservations = reservation_result.scalar_one()
                
                # Update inventory metrics
                logger.debug(
                    "Updated inventory metrics", 
                    total_inventory=total_inventory,
                    total_locations=total_locations,
                    active_reservations=active_reservations,
                )
                    
        except Exception as e:
            logger.exception("Failed to update inventory metrics")


# Global instance
_background_updater: BackgroundMetricsUpdater | None = None


async def start_background_metrics() -> None:
    """Start the background metrics updater."""
    global _background_updater
    if _background_updater is None:
        _background_updater = BackgroundMetricsUpdater()
    await _background_updater.start()


async def stop_background_metrics() -> None:
    """Stop the background metrics updater."""
    global _background_updater
    if _background_updater:
        await _background_updater.stop()