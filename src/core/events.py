"""Event publishing service for Inventory Management Service."""

import uuid

import structlog

from src.models.events import (
    TOPICS,
    AdjustmentType,
    AlertLevel,
    InventoryAdjustedEvent,
    InventoryAdjustmentData,
    InventoryReleaseData,
    InventoryReleasedEvent,
    InventoryReservedEvent,
    InventoryUpdateData,
    InventoryUpdatedEvent,
    LowStockAlertData,
    LowStockAlertEvent,
    ReservationData,
    ServiceName,
    UpdateType,
)

logger = structlog.get_logger(__name__)


class InventoryEventService:
    """
    Event publishing service for Inventory Management Service.
    
    For MVP Phase 1, this service just logs events instead of publishing to Kafka.
    Future versions will integrate with actual event streaming infrastructure.
    
    Logs events for inventory operations including:
    - Stock reservations and releases
    - Inventory adjustments
    - Low stock alerts
    - General inventory updates
    """
    
    def __init__(self) -> None:
        """Initialize the event service."""
        self.logger = logger.bind(component="event_service")
        
    async def start(self) -> None:
        """Start the event service (no-op for logging implementation)."""
        self.logger.info("Event service started (logging mode)")
    
    async def stop(self) -> None:
        """Stop the event service (no-op for logging implementation)."""
        self.logger.info("Event service stopped")
    
    async def publish_inventory_reserved(
        self,
        reservation_id: str,
        product_id: str,
        quantity: int,
        location_id: str | None = None,
        order_id: str | None = None,
        expires_at: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Log InventoryReserved event (MVP implementation)."""
        try:
            # Create event data
            reservation_data = ReservationData(
                reservation_id=reservation_id,
                product_id=product_id,
                quantity=quantity,
                location_id=location_id,
                order_id=order_id,
                expires_at=expires_at,
            )
            
            # Create event
            event = InventoryReservedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=reservation_data.dict(),
            )
            
            # Log event (instead of publishing to Kafka)
            self.logger.info(
                "Event: InventoryReserved",
                event_id=event.event_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                topic=TOPICS.INVENTORY_RESERVED,
                reservation_id=reservation_id,
                product_id=product_id,
                quantity=quantity,
                location_id=location_id,
                order_id=order_id,
            )
            
        except Exception as e:
            self.logger.exception(
                "Failed to log InventoryReserved event",
                reservation_id=reservation_id,
                product_id=product_id,
            )
    
    async def publish_inventory_released(
        self,
        reservation_id: str,
        product_id: str,
        quantity: int,
        reason: str,
        location_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Log InventoryReleased event (MVP implementation)."""
        try:
            # Create event data
            release_data = InventoryReleaseData(
                reservation_id=reservation_id,
                product_id=product_id,
                quantity=quantity,
                location_id=location_id,
                reason=reason,
            )
            
            # Create event
            event = InventoryReleasedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=release_data.dict(),
            )
            
            # Log event (instead of publishing to Kafka)
            self.logger.info(
                "Event: InventoryReleased",
                event_id=event.event_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                topic=TOPICS.INVENTORY_RELEASED,
                reservation_id=reservation_id,
                product_id=product_id,
                quantity=quantity,
                location_id=location_id,
                reason=reason,
            )
            
        except Exception as e:
            self.logger.exception(
                "Failed to log InventoryReleased event",
                reservation_id=reservation_id,
                product_id=product_id,
            )
    
    async def publish_inventory_adjusted(
        self,
        product_id: str,
        old_quantity: int,
        new_quantity: int,
        adjustment_type: str,
        location_id: str | None = None,
        reason: str | None = None,
        reference_number: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Log InventoryAdjusted event (MVP implementation)."""
        try:
            # Create event data
            adjustment_data = InventoryAdjustmentData(
                product_id=product_id,
                location_id=location_id,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                adjustment_type=AdjustmentType(adjustment_type),
                reason=reason,
                reference_number=reference_number,
            )
            
            # Create event
            event = InventoryAdjustedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=adjustment_data.dict(),
            )
            
            # Log event (instead of publishing to Kafka)
            self.logger.info(
                "Event: InventoryAdjusted",
                event_id=event.event_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                topic=TOPICS.INVENTORY_ADJUSTED,
                product_id=product_id,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                adjustment_type=adjustment_type,
                location_id=location_id,
                reason=reason,
            )
            
        except Exception as e:
            self.logger.exception(
                "Failed to log InventoryAdjusted event",
                product_id=product_id,
            )
    
    async def publish_low_stock_alert(
        self,
        product_id: str,
        current_quantity: int,
        threshold: int,
        alert_level: str,
        location_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Log LowStockAlert event (MVP implementation)."""
        try:
            # Create event data
            alert_data = LowStockAlertData(
                product_id=product_id,
                location_id=location_id,
                current_quantity=current_quantity,
                threshold=threshold,
                alert_level=AlertLevel(alert_level),
            )
            
            # Create event
            event = LowStockAlertEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=alert_data.dict(),
            )
            
            # Log event (instead of publishing to Kafka)
            self.logger.warning(
                "Event: LowStockAlert",
                event_id=event.event_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                topic=TOPICS.LOW_STOCK_ALERT,
                product_id=product_id,
                current_quantity=current_quantity,
                threshold=threshold,
                alert_level=alert_level,
                location_id=location_id,
            )
            
        except Exception as e:
            self.logger.exception(
                "Failed to log LowStockAlert event",
                product_id=product_id,
            )
    
    async def publish_inventory_updated(
        self,
        product_id: str,
        quantity: int,
        update_type: str,
        location_id: str | None = None,
        reserved_quantity: int | None = None,
        available_quantity: int | None = None,
        source_event: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Log InventoryUpdated event (MVP implementation)."""
        try:
            # Create event data
            update_data = InventoryUpdateData(
                product_id=product_id,
                location_id=location_id,
                quantity=quantity,
                reserved_quantity=reserved_quantity,
                available_quantity=available_quantity,
                update_type=UpdateType(update_type),
                source_event=source_event,
            )
            
            # Create event
            event = InventoryUpdatedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=update_data.dict(),
            )
            
            # Log event (instead of publishing to Kafka)
            self.logger.info(
                "Event: InventoryUpdated",
                event_id=event.event_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                topic=TOPICS.INVENTORY_UPDATED,
                product_id=product_id,
                quantity=quantity,
                update_type=update_type,
                location_id=location_id,
                reserved_quantity=reserved_quantity,
                available_quantity=available_quantity,
            )
            
        except Exception as e:
            self.logger.exception(
                "Failed to log InventoryUpdated event",
                product_id=product_id,
            )


# Global instance
_event_service: InventoryEventService | None = None


async def get_event_service() -> InventoryEventService:
    """Get or create the global event service instance."""
    global _event_service
    if _event_service is None:
        _event_service = InventoryEventService()
        await _event_service.start()
    return _event_service


async def close_event_service() -> None:
    """Close the global event service instance."""
    global _event_service
    if _event_service is not None:
        await _event_service.stop()
        _event_service = None