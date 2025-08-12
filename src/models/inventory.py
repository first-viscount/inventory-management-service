"""Database models for inventory management."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.core.database import Base


class LocationType(StrEnum):
    """Types of inventory locations."""
    WAREHOUSE = "warehouse"
    STORE = "store"
    ONLINE = "online"
    DROPSHIP = "dropship"


class ReservationStatus(StrEnum):
    """Status of inventory reservations."""
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"
    COMPLETED = "completed"


class AdjustmentType(StrEnum):
    """Types of inventory adjustments."""
    RESTOCK = "restock"
    DAMAGE = "damage"
    THEFT = "theft"
    CORRECTION = "correction"
    RETURN = "return"
    MANUAL = "manual"


class Location(Base):
    """Inventory location model."""
    
    __tablename__ = "locations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    type: Mapped[LocationType] = mapped_column(Enum(LocationType), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationships
    inventory_items: Mapped[list["Inventory"]] = relationship(
        "Inventory", 
        back_populates="location",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_locations_type_active", "type", "active"),
    )

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name='{self.name}', type='{self.type}')>"


class Inventory(Base):
    """Inventory tracking model."""
    
    __tablename__ = "inventory"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id"),
        nullable=False,
    )
    quantity_available: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0,
    )
    quantity_reserved: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0,
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=10,
    )
    reorder_quantity: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=100,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationships
    location: Mapped[Location] = relationship("Location", back_populates="inventory_items")
    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation",
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    adjustments: Mapped[list["InventoryAdjustment"]] = relationship(
        "InventoryAdjustment",
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_inventory_product_location", "product_id", "location_id", unique=True),
        Index("ix_inventory_low_stock", "product_id", "quantity_available", "reorder_point"),
    )

    @property
    def total_quantity(self) -> int:
        """Total quantity (available + reserved)."""
        return self.quantity_available + self.quantity_reserved
    
    @property
    def is_low_stock(self) -> bool:
        """Check if inventory is below reorder point."""
        return self.quantity_available <= self.reorder_point

    def __repr__(self) -> str:
        return (
            f"<Inventory(id={self.id}, product_id={self.product_id}, "
            f"available={self.quantity_available}, reserved={self.quantity_reserved})>"
        )


class Reservation(Base):
    """Inventory reservation model."""
    
    __tablename__ = "reservations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.id"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
    )
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus), 
        nullable=False, 
        default=ReservationStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationships
    inventory: Mapped[Inventory] = relationship("Inventory", back_populates="reservations")
    
    __table_args__ = (
        Index("ix_reservations_order_status", "order_id", "status"),
        Index("ix_reservations_expires_status", "expires_at", "status"),
        Index("ix_reservations_product_status", "product_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Reservation(id={self.id}, order_id={self.order_id}, "
            f"quantity={self.quantity}, status='{self.status}')>"
        )


class InventoryAdjustment(Base):
    """Inventory adjustment model."""
    
    __tablename__ = "inventory_adjustments"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.id"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
    )
    adjustment_type: Mapped[AdjustmentType] = mapped_column(
        Enum(AdjustmentType), 
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    inventory: Mapped[Inventory] = relationship("Inventory", back_populates="adjustments")
    
    __table_args__ = (
        Index("ix_adjustments_product_type", "product_id", "adjustment_type"),
        Index("ix_adjustments_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryAdjustment(id={self.id}, product_id={self.product_id}, "
            f"type='{self.adjustment_type}', quantity={self.quantity})>"
        )