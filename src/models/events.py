"""Internal event models for the Inventory Management Service."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceName(StrEnum):
    """Service names for event correlation."""
    INVENTORY_MANAGEMENT = "inventory-management-service"
    ORDER_MANAGEMENT = "order-management-service"
    PRODUCT_CATALOG = "product-catalog-service"


class AdjustmentType(StrEnum):
    """Types of inventory adjustments."""
    RESTOCK = "restock"
    DAMAGE = "damage"
    THEFT = "theft"
    CORRECTION = "correction"
    RETURN = "return"
    MANUAL = "manual"


class AlertLevel(StrEnum):
    """Alert levels for low stock notifications."""
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class UpdateType(StrEnum):
    """Types of inventory updates."""
    RESERVATION = "reservation"
    RELEASE = "release"
    ADJUSTMENT = "adjustment"
    RESTOCK = "restock"
    MANUAL = "manual"


# Base Event Model
class BaseEvent(BaseModel):
    """Base model for all events."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str
    source_service: ServiceName
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = Field(default="1.0")


# Event Data Models
class ReservationData(BaseModel):
    """Data for inventory reservation events."""
    
    reservation_id: str
    product_id: str
    quantity: int
    location_id: str | None = None
    order_id: str | None = None
    expires_at: str | None = None


class InventoryReleaseData(BaseModel):
    """Data for inventory release events."""
    
    reservation_id: str
    product_id: str
    quantity: int
    location_id: str | None = None
    reason: str


class InventoryAdjustmentData(BaseModel):
    """Data for inventory adjustment events."""
    
    product_id: str
    location_id: str | None = None
    old_quantity: int
    new_quantity: int
    adjustment_type: AdjustmentType
    reason: str | None = None
    reference_number: str | None = None


class LowStockAlertData(BaseModel):
    """Data for low stock alert events."""
    
    product_id: str
    location_id: str | None = None
    current_quantity: int
    threshold: int
    alert_level: AlertLevel


class InventoryUpdateData(BaseModel):
    """Data for general inventory update events."""
    
    product_id: str
    location_id: str | None = None
    quantity: int
    reserved_quantity: int | None = None
    available_quantity: int | None = None
    update_type: UpdateType
    source_event: str | None = None


# Event Models
class InventoryReservedEvent(BaseEvent):
    """Event published when inventory is reserved."""
    
    event_type: str = Field(default="InventoryReserved")
    data: dict  # Will contain ReservationData as dict


class InventoryReleasedEvent(BaseEvent):
    """Event published when inventory reservation is released."""
    
    event_type: str = Field(default="InventoryReleased")
    data: dict  # Will contain InventoryReleaseData as dict


class InventoryAdjustedEvent(BaseEvent):
    """Event published when inventory is adjusted."""
    
    event_type: str = Field(default="InventoryAdjusted")
    data: dict  # Will contain InventoryAdjustmentData as dict


class LowStockAlertEvent(BaseEvent):
    """Event published when stock falls below threshold."""
    
    event_type: str = Field(default="LowStockAlert")
    data: dict  # Will contain LowStockAlertData as dict


class InventoryUpdatedEvent(BaseEvent):
    """Event published for general inventory updates."""
    
    event_type: str = Field(default="InventoryUpdated")
    data: dict  # Will contain InventoryUpdateData as dict


# Event Topics (for future Kafka integration)
class EventTopics:
    """Constants for event topics."""
    
    INVENTORY_RESERVED = "inventory.reserved"
    INVENTORY_RELEASED = "inventory.released"
    INVENTORY_ADJUSTED = "inventory.adjusted"
    LOW_STOCK_ALERT = "inventory.low-stock-alert"
    INVENTORY_UPDATED = "inventory.updated"


# Create a Topics instance for easy access
TOPICS = EventTopics()