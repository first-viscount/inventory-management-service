"""Test reservation management endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_reservations_empty(client: AsyncClient) -> None:
    """Test listing reservations when none exist."""
    response = await client.get("/api/v1/reservations")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_reservation_after_creation(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test getting a specific reservation after creation."""
    # Setup: Create location, inventory, and make a reservation
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Create reservation
    order_id = str(uuid.uuid4())
    reserve_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order_id,
        "expires_minutes": 60,
    }
    
    reserve_response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
    assert reserve_response.status_code == 201
    reservation_id = reserve_response.json()["reservation"]["id"]
    
    # Get the reservation
    response = await client.get(f"/api/v1/reservations/{reservation_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == reservation_id
    assert data["product_id"] == product_id
    assert data["order_id"] == order_id
    assert data["quantity"] == 10
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_nonexistent_reservation(client: AsyncClient) -> None:
    """Test getting a nonexistent reservation returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/reservations/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_reservations_by_order(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test listing reservations filtered by order ID."""
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
    
    # Create reservations for different orders
    order1_id = str(uuid.uuid4())
    order2_id = str(uuid.uuid4())
    
    # Reservation 1 for order 1
    reserve_data1 = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order1_id,
        "expires_minutes": 60,
    }
    response1 = await client.post("/api/v1/inventory/reserve", json=reserve_data1)
    assert response1.status_code == 201
    
    # Reservation 2 for order 2
    reserve_data2 = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 5,
        "order_id": order2_id,
        "expires_minutes": 60,
    }
    response2 = await client.post("/api/v1/inventory/reserve", json=reserve_data2)
    assert response2.status_code == 201
    
    # Get reservations for order 1 only
    response = await client.get(f"/api/v1/reservations?order_id={order1_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["order_id"] == order1_id
    assert data[0]["quantity"] == 10


@pytest.mark.asyncio
async def test_list_reservations_by_product(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test listing reservations filtered by product ID."""
    # Setup: Create location and two products with inventory
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product1_id = str(uuid.uuid4())
    product2_id = str(uuid.uuid4())
    
    # Create inventory for both products
    for product_id in [product1_id, product2_id]:
        inventory_data = {
            **sample_inventory_data,
            "product_id": product_id,
            "location_id": location_id,
        }
        await client.post("/api/v1/inventory", json=inventory_data)
    
    # Create reservations for both products
    for i, product_id in enumerate([product1_id, product2_id], 1):
        reserve_data = {
            "product_id": product_id,
            "location_id": location_id,
            "quantity": i * 5,  # 5 and 10
            "order_id": str(uuid.uuid4()),
            "expires_minutes": 60,
        }
        response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
        assert response.status_code == 201
    
    # Get reservations for product 1 only
    response = await client.get(f"/api/v1/reservations?product_id={product1_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["product_id"] == product1_id
    assert data[0]["quantity"] == 5


@pytest.mark.asyncio
async def test_list_reservations_by_status(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test listing reservations filtered by status."""
    # Setup: Create location, inventory, and reservation
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Create reservation
    order_id = str(uuid.uuid4())
    reserve_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order_id,
        "expires_minutes": 60,
    }
    
    reserve_response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
    assert reserve_response.status_code == 201
    reservation_id = reserve_response.json()["reservation"]["id"]
    
    # List active reservations
    response = await client.get("/api/v1/reservations?status=active")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "active"
    assert data[0]["id"] == reservation_id
    
    # List completed reservations (should be empty)
    response = await client.get("/api/v1/reservations?status=completed")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_complete_reservation(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test marking a reservation as completed."""
    # Setup: Create location, inventory, and reservation
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Create reservation
    order_id = str(uuid.uuid4())
    reserve_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order_id,
        "expires_minutes": 60,
    }
    
    reserve_response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
    assert reserve_response.status_code == 201
    reservation_id = reserve_response.json()["reservation"]["id"]
    
    # Complete the reservation
    response = await client.post(f"/api/v1/reservations/{reservation_id}/complete")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == reservation_id
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_complete_nonexistent_reservation(client: AsyncClient) -> None:
    """Test completing a nonexistent reservation returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.post(f"/api/v1/reservations/{fake_id}/complete")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_release_reservation_via_endpoint(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test releasing a reservation via the reservation endpoint."""
    # Setup: Create location, inventory, and reservation
    location_response = await client.post("/api/v1/locations", json=sample_location_data)
    location_id = location_response.json()["id"]
    
    product_id = str(uuid.uuid4())
    inventory_data = {
        **sample_inventory_data,
        "product_id": product_id,
        "location_id": location_id,
    }
    await client.post("/api/v1/inventory", json=inventory_data)
    
    # Create reservation
    order_id = str(uuid.uuid4())
    reserve_data = {
        "product_id": product_id,
        "location_id": location_id,
        "quantity": 10,
        "order_id": order_id,
        "expires_minutes": 60,
    }
    
    reserve_response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
    assert reserve_response.status_code == 201
    reservation_id = reserve_response.json()["reservation"]["id"]
    
    # Release the reservation
    response = await client.post(f"/api/v1/reservations/{reservation_id}/release")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == reservation_id
    assert data["status"] == "released"
    
    # Verify inventory was released back
    inventory_response = await client.get(f"/api/v1/inventory/{product_id}")
    assert inventory_response.status_code == 200
    inventory_data = inventory_response.json()
    assert inventory_data["total_available"] == 100  # Back to original
    assert inventory_data["total_reserved"] == 0


@pytest.mark.asyncio
async def test_release_nonexistent_reservation(client: AsyncClient) -> None:
    """Test releasing a nonexistent reservation returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.post(f"/api/v1/reservations/{fake_id}/release")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_expired_reservations_empty(client: AsyncClient) -> None:
    """Test getting expired reservations when none exist."""
    response = await client.get("/api/v1/reservations/expired")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio 
async def test_pagination_limits(client: AsyncClient, sample_location_data, sample_inventory_data) -> None:
    """Test pagination parameters work correctly."""
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
    
    # Create multiple reservations
    reservation_ids = []
    for i in range(5):
        order_id = str(uuid.uuid4())
        reserve_data = {
            "product_id": product_id,
            "location_id": location_id,
            "quantity": 2,  # Small quantity to avoid exceeding available
            "order_id": order_id,
            "expires_minutes": 60,
        }
        
        response = await client.post("/api/v1/inventory/reserve", json=reserve_data)
        assert response.status_code == 201
        reservation_ids.append(response.json()["reservation"]["id"])
    
    # Test limit parameter
    response = await client.get("/api/v1/reservations?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Test offset parameter
    response = await client.get("/api/v1/reservations?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2