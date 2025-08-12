"""Test location management endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_location(client: AsyncClient, sample_location_data) -> None:
    """Test creating a new location."""
    response = await client.post("/api/v1/locations", json=sample_location_data)
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["name"] == sample_location_data["name"]
    assert data["address"] == sample_location_data["address"]
    assert data["type"] == sample_location_data["type"]
    assert data["active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_location_duplicate_name(client: AsyncClient, sample_location_data) -> None:
    """Test creating location with duplicate name fails."""
    # Create first location
    response = await client.post("/api/v1/locations", json=sample_location_data)
    assert response.status_code == 201
    
    # Try to create another with same name
    response = await client.post("/api/v1/locations", json=sample_location_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_location(client: AsyncClient, sample_location_data) -> None:
    """Test getting a location by ID."""
    # Create location first
    response = await client.post("/api/v1/locations", json=sample_location_data)
    assert response.status_code == 201
    created_location = response.json()
    location_id = created_location["id"]
    
    # Get the location
    response = await client.get(f"/api/v1/locations/{location_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == location_id
    assert data["name"] == sample_location_data["name"]
    assert data["type"] == sample_location_data["type"]


@pytest.mark.asyncio
async def test_get_nonexistent_location(client: AsyncClient) -> None:
    """Test getting a nonexistent location returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/locations/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_locations(client: AsyncClient, sample_location_data) -> None:
    """Test listing locations."""
    # Create a few locations
    locations_data = [
        {**sample_location_data, "name": "Warehouse 1"},
        {**sample_location_data, "name": "Store 1", "type": "store"},
        {**sample_location_data, "name": "Online", "type": "online"},
    ]
    
    created_locations = []
    for location_data in locations_data:
        response = await client.post("/api/v1/locations", json=location_data)
        assert response.status_code == 201
        created_locations.append(response.json())
    
    # List all locations
    response = await client.get("/api/v1/locations")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 3
    assert all(loc["active"] for loc in data)


@pytest.mark.asyncio
async def test_list_locations_by_type(client: AsyncClient, sample_location_data) -> None:
    """Test listing locations filtered by type."""
    # Create locations of different types
    warehouse_data = {**sample_location_data, "name": "Warehouse 1", "type": "warehouse"}
    store_data = {**sample_location_data, "name": "Store 1", "type": "store"}
    
    await client.post("/api/v1/locations", json=warehouse_data)
    await client.post("/api/v1/locations", json=store_data)
    
    # Get warehouses only
    response = await client.get("/api/v1/locations?type=warehouse")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "warehouse"
    assert data[0]["name"] == "Warehouse 1"


@pytest.mark.asyncio
async def test_get_locations_by_type_endpoint(client: AsyncClient, sample_location_data) -> None:
    """Test the dedicated endpoint for getting locations by type."""
    # Create warehouses
    warehouse_data = {**sample_location_data, "name": "Warehouse 1", "type": "warehouse"}
    response = await client.post("/api/v1/locations", json=warehouse_data)
    assert response.status_code == 201
    
    # Get warehouses via type endpoint
    response = await client.get("/api/v1/locations/types/warehouse")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "warehouse"


@pytest.mark.asyncio
async def test_update_location(client: AsyncClient, sample_location_data) -> None:
    """Test updating a location."""
    # Create location first
    response = await client.post("/api/v1/locations", json=sample_location_data)
    assert response.status_code == 201
    created_location = response.json()
    location_id = created_location["id"]
    
    # Update the location
    update_data = {
        "name": "Updated Warehouse",
        "address": "456 New St, New City, NC 67890",
        "type": "store",
    }
    
    response = await client.put(f"/api/v1/locations/{location_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["address"] == update_data["address"]
    assert data["type"] == update_data["type"]
    assert data["id"] == location_id


@pytest.mark.asyncio
async def test_update_location_partial(client: AsyncClient, sample_location_data) -> None:
    """Test partial update of a location."""
    # Create location first
    response = await client.post("/api/v1/locations", json=sample_location_data)
    assert response.status_code == 201
    created_location = response.json()
    location_id = created_location["id"]
    original_name = created_location["name"]
    
    # Update only the address
    update_data = {"address": "New Address Only"}
    
    response = await client.put(f"/api/v1/locations/{location_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["address"] == update_data["address"]
    assert data["name"] == original_name  # Should remain unchanged


@pytest.mark.asyncio
async def test_update_nonexistent_location(client: AsyncClient) -> None:
    """Test updating a nonexistent location returns 404."""
    fake_id = str(uuid.uuid4())
    update_data = {"name": "New Name"}
    
    response = await client.put(f"/api/v1/locations/{fake_id}", json=update_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_location(client: AsyncClient, sample_location_data) -> None:
    """Test deactivating a location."""
    # Create location first
    response = await client.post("/api/v1/locations", json=sample_location_data)
    assert response.status_code == 201
    created_location = response.json()
    location_id = created_location["id"]
    
    # Deactivate the location
    response = await client.delete(f"/api/v1/locations/{location_id}")
    assert response.status_code == 204
    
    # Verify location is deactivated by getting it directly
    response = await client.get(f"/api/v1/locations/{location_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False


@pytest.mark.asyncio
async def test_deactivate_nonexistent_location(client: AsyncClient) -> None:
    """Test deactivating a nonexistent location returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"/api/v1/locations/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_includes_inactive_when_requested(client: AsyncClient, sample_location_data) -> None:
    """Test listing locations includes inactive when requested."""
    # Create location
    response = await client.post("/api/v1/locations", json=sample_location_data)
    assert response.status_code == 201
    location_id = response.json()["id"]
    
    # Deactivate it
    response = await client.delete(f"/api/v1/locations/{location_id}")
    assert response.status_code == 204
    
    # List without including inactive
    response = await client.get("/api/v1/locations")
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # List including inactive
    response = await client.get("/api/v1/locations?include_inactive=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["active"] is False