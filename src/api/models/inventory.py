"""API models for inventory operations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.inventory import AdjustmentType, LocationType, ReservationStatus


# Request Models
class ReserveInventoryRequest(BaseModel):
    """Request to reserve inventory."""
    
    model_config = ConfigDict(from_attributes=True)
    
    product_id: uuid.UUID = Field(..., description="Product ID to reserve")
    location_id: uuid.UUID = Field(..., description="Location where inventory is reserved")
    quantity: int = Field(..., gt=0, description="Quantity to reserve")
    order_id: uuid.UUID = Field(..., description="Order ID this reservation is for")
    expires_minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Minutes until reservation expires (1-1440)",
    )


class ReleaseInventoryRequest(BaseModel):
    """Request to release inventory reservation."""
    
    model_config = ConfigDict(from_attributes=True)
    
    product_id: uuid.UUID = Field(..., description="Product ID to release")
    location_id: uuid.UUID = Field(..., description="Location where inventory is reserved")
    quantity: int = Field(..., gt=0, description="Quantity to release")
    order_id: uuid.UUID = Field(..., description="Order ID this release is for")


class AdjustInventoryRequest(BaseModel):
    """Request to adjust inventory."""
    
    model_config = ConfigDict(from_attributes=True)
    
    product_id: uuid.UUID = Field(..., description="Product ID to adjust")
    location_id: uuid.UUID = Field(..., description="Location where inventory is adjusted")
    quantity_change: int = Field(
        ..., 
        description="Quantity change (positive to add, negative to remove)",
    )
    adjustment_type: AdjustmentType = Field(..., description="Type of adjustment")
    reason: str | None = Field(None, description="Optional reason for adjustment")
    created_by: str = Field(default="api", description="Who made the adjustment")


class CreateLocationRequest(BaseModel):
    """Request to create a location."""
    
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=255, description="Location name")
    address: str | None = Field(None, description="Optional address")
    type: LocationType = Field(..., description="Location type")


class UpdateLocationRequest(BaseModel):
    """Request to update a location."""
    
    model_config = ConfigDict(from_attributes=True)
    
    name: str | None = Field(None, min_length=1, max_length=255, description="Location name")
    address: str | None = Field(None, description="Address")
    type: LocationType | None = Field(None, description="Location type")
    active: bool | None = Field(None, description="Whether location is active")


class CreateInventoryRequest(BaseModel):
    """Request to create inventory record."""
    
    model_config = ConfigDict(from_attributes=True)
    
    product_id: uuid.UUID = Field(..., description="Product ID")
    location_id: uuid.UUID = Field(..., description="Location ID")
    quantity_available: int = Field(default=0, ge=0, description="Initial quantity")
    reorder_point: int = Field(default=10, ge=0, description="Reorder point")
    reorder_quantity: int = Field(default=100, ge=1, description="Reorder quantity")


class UpdateInventoryRequest(BaseModel):
    """Request to update inventory settings."""
    
    model_config = ConfigDict(from_attributes=True)
    
    reorder_point: int | None = Field(None, ge=0, description="Reorder point")
    reorder_quantity: int | None = Field(None, ge=1, description="Reorder quantity")


# Response Models
class LocationResponse(BaseModel):
    """Response model for location."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    address: str | None
    type: LocationType
    active: bool
    created_at: datetime
    updated_at: datetime


class InventoryResponse(BaseModel):
    """Response model for inventory."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity_available: int
    quantity_reserved: int
    total_quantity: int
    reorder_point: int
    reorder_quantity: int
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime
    location: LocationResponse


class ReservationResponse(BaseModel):
    """Response model for reservation."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    product_id: uuid.UUID
    order_id: uuid.UUID
    quantity: int
    expires_at: datetime
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime


class InventoryAdjustmentResponse(BaseModel):
    """Response model for inventory adjustment."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    product_id: uuid.UUID
    adjustment_type: AdjustmentType
    quantity: int
    reason: str | None
    created_by: str
    created_at: datetime


class LowStockItem(BaseModel):
    """Low stock item information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    product_id: uuid.UUID
    location: LocationResponse
    quantity_available: int
    reorder_point: int
    reorder_quantity: int
    shortage: int = Field(..., description="How much below reorder point")


class InventoryOperationResponse(BaseModel):
    """Response for inventory operations."""
    
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    message: str
    inventory: InventoryResponse | None = None
    reservation: ReservationResponse | None = None


class InventoryStatsResponse(BaseModel):
    """Response for inventory statistics."""
    
    model_config = ConfigDict(from_attributes=True)
    
    product_id: uuid.UUID
    total_available: int
    total_reserved: int
    locations: list[InventoryResponse]