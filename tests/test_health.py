"""Test health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Test basic health check endpoint."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "inventory-management-service"
    assert data["version"] == "0.1.0"
    assert "database" in data


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient) -> None:
    """Test readiness check endpoint."""
    response = await client.get("/health/ready")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ready"
    assert data["service"] == "inventory-management-service"
    assert data["version"] == "0.1.0"
    assert "checks" in data
    assert "database" in data["checks"]


@pytest.mark.asyncio
async def test_liveness_check(client: AsyncClient) -> None:
    """Test liveness check endpoint."""
    response = await client.get("/health/live")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "alive"
    assert data["service"] == "inventory-management-service"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_service_info(client: AsyncClient) -> None:
    """Test root service info endpoint."""
    response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["service"] == "inventory-management-service"
    assert data["version"] == "0.1.0"
    assert "database" in data