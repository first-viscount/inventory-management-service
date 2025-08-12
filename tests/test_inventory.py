"""Test inventory management endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_inventory(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test creating a new inventory record."""
    # Create location first
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    assert location_response.status_code == 201
    location_id = location_response.json()["id"]
    
    # Create inventory
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    
    response = await client.post("/api/v1/inventory", json=inventory_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["product_id"] == product_id
    assert data["location_id"] == location_id
    assert data["quantity_available"] == sample_inventory_data["quantity_available"]
    assert data["quantity_reserved"] == 0
    assert data["total_quantity"] == sample_inventory_data["quantity_available"]
    assert data["is_low_stock"] is False  # 100 > 10


@pytest.mark.asyncio
async def test_create_inventory_nonexistent_location(client: AsyncClient, sample_inventory_data) -> None:
    """Test creating inventory for nonexistent location fails."""
    fake_location_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": str(uuid.uuid4()),
        "location_id": fake_location_id,
    }
    
    response = await client.post("/api/v1/inventory", json=inventory_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_duplicate_inventory(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test creating duplicate inventory record fails."""
    # Create location
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    
    # Create first inventory
    response = await client.post("/api/v1/inventory", json=inventory_data)
    assert response.status_code == 201
    
    # Try to create duplicate
    response = await client.post("/api/v1/inventory", json=inventory_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_inventory_stats(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test getting inventory stats for a product."""
    # Setup: Create location and inventory
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Get inventory stats
    response = await client.get(f"/api/v1/inventory/{product_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["product_id"] == product_id
    assert data["total_available"] == sample_inventory_data["quantity_available"]
    assert data["total_reserved"] == 0
    assert len(data["locations"]) == 1
    assert data["locations"][0]["location"]["name"] == sample_location_data["name"]


@pytest.mark.asyncio
async def test_get_inventory_nonexistent_product(client: AsyncClient) -> None:
    """Test getting inventory for nonexistent product returns 404."""
    fake_product_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/inventory/{fake_product_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reserve_inventory(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test reserving inventory."""
    # Setup: Create location and inventory
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Reserve inventory
    order_id = str(uuid.uuid4())
    reserve_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order_id,
        "expires_minutes": 60,
    }
    
    response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["success"] is True
    assert data["inventory"]["quantity_available"] == 90  # 100 - 10
    assert data["inventory"]["quantity_reserved"] == 10
    assert data["reservation"]["order_id"] == order_id
    assert data["reservation"]["quantity"] == 10


@pytest.mark.asyncio
async def test_reserve_insufficient_inventory(client: AsyncClient, sample_location_data) -> None:
    """Test reserving more inventory than available fails."""
    # Setup: Create location and low inventory
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity_available": 5,  # Only 5 available
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Try to reserve more than available
    order_id = str(uuid.uuid4())
    reserve_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,  # More than available
        "order_id": order_id,
        "expires_minutes": 60,
    }
    
    response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
    assert response.status_code == 409  # Insufficient stock


@pytest.mark.asyncio
async def test_release_inventory(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test releasing reserved inventory."""
    # Setup: Create location and inventory, then reserve some
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Reserve inventory first
    order_id = str(uuid.uuid4())
    reserve_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order_id,
        "expires_minutes": 60,
    }
    
    response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
    assert response.status_code == 201
    
    # Release the reservation
    release_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order_id,
    }
    
    response = await client.post("/api/v1/inventory/release", json=release_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["inventory"]["quantity_available"] == 100  # Back to original
    assert data["inventory"]["quantity_reserved"] == 0


@pytest.mark.asyncio
async def test_adjust_inventory_positive(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test adjusting inventory upward (adding stock)."""
    # Setup: Create location and inventory
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Adjust inventory upward
    adjust_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity_change": 50,  # Add 50 units
        "adjustment_type": "restock",
        "reason": "New shipment arrived",
        "created_by": "test_user",
    }
    
    response = await client.post("/api/v1/inventory/adjust", json=adjust_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["inventory"]["quantity_available"] == 150  # 100 + 50
    assert "Added 50 units" in data["message"]


@pytest.mark.asyncio
async def test_adjust_inventory_negative(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test adjusting inventory downward (removing stock)."""
    # Setup: Create location and inventory
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Adjust inventory downward
    adjust_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity_change": -20,  # Remove 20 units
        "adjustment_type": "damage",
        "reason": "Damaged during handling",
        "created_by": "test_user",
    }
    
    response = await client.post("/api/v1/inventory/adjust", json=adjust_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["inventory"]["quantity_available"] == 80  # 100 - 20
    assert "Removed 20 units" in data["message"]


@pytest.mark.asyncio
async def test_adjust_inventory_negative_overflow(client: AsyncClient, sample_location_data) -> None:
    """Test adjusting inventory below zero fails."""
    # Setup: Create location and low inventory
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity_available": 10,  # Only 10 available
        "reorder_point": 5,
        "reorder_quantity": 50,
    }
    
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Try to remove more than available
    adjust_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity_change": -20,  # Remove more than available
        "adjustment_type": "damage",
        "created_by": "test_user",
    }
    
    response = await client.post("/api/v1/inventory/adjust", json=adjust_data)
    assert response.status_code == 400  # Bad request


@pytest.mark.asyncio
async def test_get_low_stock_items(client: AsyncClient, sample_location_data) -> None:
    """Test getting low stock items."""
    # Setup: Create location
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    # Create some inventory items, some below reorder point
    inventories = [
        {
            "product_id": str(uuid.uuid4()),
            "location_id": location_id,
            "quantity_available": 5,   # Below reorder point (10)
            "reorder_point": 10,
            "reorder_quantity": 50,
        },
        {
            "product_id": str(uuid.uuid4()),
            "location_id": location_id,
            "quantity_available": 50,  # Above reorder point
            "reorder_point": 10,
            "reorder_quantity": 50,
        },
        {
            "product_id": str(uuid.uuid4()),
            "location_id": location_id,
            "quantity_available": 8,   # Below reorder point (15)
            "reorder_point": 15,
            "reorder_quantity": 50,
        },
    ]
    
    for inventory_data in inventories:
        response = await client.post("/api/v1/inventory", json=inventory_data)
        assert response.status_code == 201
    
    # Get low stock items
    response = await client.get("/api/v1/inventory/low-stock")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2  # Only 2 are below reorder point
    
    # Verify sorting by shortage (most critical first)
    assert data[0]["shortage"] >= data[1]["shortage"]
    
    # Check that all returned items have shortage > 0
    for item in data:
        assert item["quantity_available"] <= item["reorder_point"]
        assert item["shortage"] > 0


@pytest.mark.asyncio
async def test_get_low_stock_items_filtered_by_location(client: AsyncClient, sample_location_data) -> None:
    """Test getting low stock items filtered by location."""
    # Setup: Create two locations
    location1_response = await client.post("/api/v1/locations", json={
        **sample_location_data, "name": "Warehouse 1",
    })
    location1_id = location1_response.json()["id"]
    
    location2_response = await client.post("/api/v1/locations", json={
        **sample_location_data, "name": "Warehouse 2",
    })
    location2_id = location2_response.json()["id"]
    
    # Create low stock in location 1
    inventory_data = {
        "product_id": str(uuid.uuid4()),
        "location_id": location1_id,
        "quantity_available": 5,   # Below reorder point
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Create normal stock in location 2
    inventory_data = {
        "product_id": str(uuid.uuid4()),
        "location_id": location2_id,
        "quantity_available": 50,  # Above reorder point
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Get low stock for location 1 only
    response = await client.get(f"/api/v1/inventory/low-stock?location_id={location1_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1  # Only location 1 has low stock
    assert data[0]["location"]["id"] == location1_id