"""Event publishing service for Inventory Management Service."""

import uuid
from typing import Optional

import structlog

from src.models.events import (
    InventoryReservedEvent,
    InventoryReleasedEvent,
    InventoryAdjustedEvent,
    LowStockAlertEvent,
    InventoryUpdatedEvent,
    ReservationData,
    InventoryReleaseData,
    InventoryAdjustmentData,
    LowStockAlertData,
    InventoryUpdateData,
    ServiceName,
    AdjustmentType,
    AlertLevel,
    UpdateType,
    TOPICS,
)

from .config import settings


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
    
    def __init__(self):
        """Initialize the event service."""
        self.logger = logger.bind(component="event_service")
        
    async def start(self):
        """Start the event service (no-op for logging implementation)."""
        self.logger.info("Event service started (logging mode)")
    
    async def stop(self):
        """Stop the event service (no-op for logging implementation)."""
        self.logger.info("Event service stopped")
    
    async def publish_inventory_reserved(
        self,
        reservation_id: str,
        product_id: str,
        quantity: int,
        location_id: Optional[str] = None,
        order_id: Optional[str] = None,
        expires_at: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Log InventoryReserved event (MVP implementation)."""
        try:
            # Create event data
            reservation_data = ReservationData(
                reservation_id=reservation_id,
                product_id=product_id,
                quantity=quantity,
                location_id=location_id,
                order_id=order_id,
                expires_at=expires_at
            )
            
            # Create event
            event = InventoryReservedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=reservation_data.dict()
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
                order_id=order_id
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log InventoryReserved event",
                reservation_id=reservation_id,
                product_id=product_id,
                error=str(e)
            )
    
    async def publish_inventory_released(
        self,
        reservation_id: str,
        product_id: str,
        quantity: int,
        reason: str,
        location_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Log InventoryReleased event (MVP implementation)."""
        try:
            # Create event data
            release_data = InventoryReleaseData(
                reservation_id=reservation_id,
                product_id=product_id,
                quantity=quantity,
                location_id=location_id,
                reason=reason
            )
            
            # Create event
            event = InventoryReleasedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=release_data.dict()
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
                reason=reason
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log InventoryReleased event",
                reservation_id=reservation_id,
                product_id=product_id,
                error=str(e)
            )
    
    async def publish_inventory_adjusted(
        self,
        product_id: str,
        old_quantity: int,
        new_quantity: int,
        adjustment_type: str,
        location_id: Optional[str] = None,
        reason: Optional[str] = None,
        reference_number: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
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
                reference_number=reference_number
            )
            
            # Create event
            event = InventoryAdjustedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=adjustment_data.dict()
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
                reason=reason
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log InventoryAdjusted event",
                product_id=product_id,
                error=str(e)
            )
    
    async def publish_low_stock_alert(
        self,
        product_id: str,
        current_quantity: int,
        threshold: int,
        alert_level: str,
        location_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Log LowStockAlert event (MVP implementation)."""
        try:
            # Create event data
            alert_data = LowStockAlertData(
                product_id=product_id,
                location_id=location_id,
                current_quantity=current_quantity,
                threshold=threshold,
                alert_level=AlertLevel(alert_level)
            )
            
            # Create event
            event = LowStockAlertEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=alert_data.dict()
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
                location_id=location_id
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log LowStockAlert event",
                product_id=product_id,
                error=str(e)
            )
    
    async def publish_inventory_updated(
        self,
        product_id: str,
        quantity: int,
        update_type: str,
        location_id: Optional[str] = None,
        reserved_quantity: Optional[int] = None,
        available_quantity: Optional[int] = None,
        source_event: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
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
                source_event=source_event
            )
            
            # Create event
            event = InventoryUpdatedEvent(
                correlation_id=correlation_id or str(uuid.uuid4()),
                source_service=ServiceName.INVENTORY_MANAGEMENT,
                data=update_data.dict()
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
                available_quantity=available_quantity
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log InventoryUpdated event",
                product_id=product_id,
                error=str(e)
            )


# Global instance
_event_service: Optional[InventoryEventService] = None


async def get_event_service() -> InventoryEventService:
    """Get or create the global event service instance."""
    global _event_service
    if _event_service is None:
        _event_service = InventoryEventService()
        await _event_service.start()
    return _event_service


async def close_event_service():
    """Close the global event service instance."""
    global _event_service
    if _event_service is not None:
        await _event_service.stop()
        _event_service = None