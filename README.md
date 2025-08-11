# Inventory Management Service

A comprehensive inventory tracking and stock management service for the First Viscount e-commerce platform. This service provides real-time inventory tracking, stock reservations, and multi-location inventory management.

## Features

### Core Functionality
- **Real-time Inventory Tracking**: Track available and reserved stock across multiple locations
- **Stock Reservations**: Reserve inventory for orders with automatic expiration
- **Inventory Adjustments**: Handle stock additions, corrections, damage, theft, and other adjustments
- **Multi-location Support**: Manage inventory across warehouses, stores, dropship locations, and online inventory
- **Low Stock Alerts**: Identify products below reorder points for automated reordering
- **Complete Audit Trail**: Track all inventory movements and changes

### API Endpoints

#### Inventory Management
- `GET /api/v1/inventory/{product_id}` - Get current stock for a product across all locations
- `POST /api/v1/inventory/reserve` - Reserve inventory for an order
- `POST /api/v1/inventory/release` - Release a reservation
- `POST /api/v1/inventory/adjust` - Adjust stock levels (add/remove inventory)
- `GET /api/v1/inventory/low-stock` - Get products with low stock
- `POST /api/v1/inventory` - Create inventory record for a product at a location

#### Reservation Management
- `GET /api/v1/reservations` - List active reservations with filtering
- `GET /api/v1/reservations/{reservation_id}` - Get reservation details
- `POST /api/v1/reservations/{reservation_id}/complete` - Mark reservation as completed (consumed)
- `POST /api/v1/reservations/{reservation_id}/release` - Release reservation back to available stock
- `GET /api/v1/reservations/expired` - Get expired reservations for cleanup

#### Location Management
- `GET /api/v1/locations` - List all locations with filtering
- `GET /api/v1/locations/{location_id}` - Get location details
- `POST /api/v1/locations` - Create a new location
- `PUT /api/v1/locations/{location_id}` - Update location information
- `DELETE /api/v1/locations/{location_id}` - Deactivate location (soft delete)
- `GET /api/v1/locations/types/{type}` - Get locations by type

#### Health & Monitoring
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check for Kubernetes
- `GET /health/live` - Liveness check for Kubernetes
- `GET /metrics` - Prometheus metrics endpoint

## Architecture

### Database Models

#### Locations
- Support for different location types: warehouse, store, online, dropship
- Soft deletion with active/inactive status
- Address and type information for each location

#### Inventory
- Product-location specific inventory tracking
- Separate tracking of available and reserved quantities
- Configurable reorder points and quantities
- Automatic low-stock detection

#### Reservations
- Time-bound inventory reservations with expiration
- Status tracking: active, expired, released, completed
- Linked to specific orders and products

#### Inventory Adjustments
- Complete audit trail of all inventory changes
- Support for various adjustment types: restock, damage, theft, correction, return, manual
- Creator tracking and reason logging

### Key Design Patterns

#### Thread-Safe Operations
- All inventory modifications use database-level locking to prevent race conditions
- Atomic reserve/release operations to prevent overselling
- Consistent transaction boundaries

#### Event-Driven Architecture (Future)
- Ready for integration with event publishing for:
  - `InventoryReserved`
  - `InventoryReleased`
  - `InventoryAdjusted`
  - `LowStockAlert`
  - `InventoryUpdated`

#### Error Handling
- Comprehensive error responses with consistent format
- Proper HTTP status codes for different error types
- Detailed error messages for debugging

## Quick Start

### Prerequisites
- Python 3.13+
- Docker and Docker Compose
- PostgreSQL (handled by Docker)

### Development Setup

1. **Clone and setup**:
   ```bash
   cd inventory-management-service
   make dev-setup
   ```

2. **Start the service**:
   ```bash
   make run
   ```

3. **Access the service**:
   - API: http://localhost:8083
   - API Documentation: http://localhost:8083/docs
   - Grafana Dashboard: http://localhost:3001 (admin/admin)
   - Prometheus: http://localhost:9090

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f inventory-management-service

# Stop services
docker-compose down
```

### Running Tests

```bash
# Run all tests with coverage
make test-cov

# Run specific test files
python -m pytest tests/test_inventory.py -v

# Run with specific markers
python -m pytest -m "not slow" -v
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | `development` | Environment (development, staging, production) |
| `PORT` | `8083` | Service port |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |

### Database Configuration

The service uses PostgreSQL with asyncpg for async database operations. Database migrations are handled by SQLAlchemy's metadata creation for development, with Alembic ready for production migrations.

### Docker Configuration

```yaml
# docker-compose.yml
services:
  inventory-management-service:
    build: .
    ports:
      - "8083:8083"
    environment:
      - DATABASE_URL=postgresql+asyncpg://inventory_user:inventory_dev_password@postgres:5432/inventory_db
    depends_on:
      - postgres
```

## API Usage Examples

### Creating a Location

```bash
curl -X POST "http://localhost:8083/api/v1/locations" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Main Warehouse",
       "address": "123 Industrial Blvd, City, State 12345",
       "type": "warehouse"
     }'
```

### Creating Inventory

```bash
curl -X POST "http://localhost:8083/api/v1/inventory" \
     -H "Content-Type: application/json" \
     -d '{
       "product_id": "550e8400-e29b-41d4-a716-446655440000",
       "location_id": "660e8400-e29b-41d4-a716-446655440000",
       "quantity_available": 100,
       "reorder_point": 20,
       "reorder_quantity": 100
     }'
```

### Reserving Inventory

```bash
curl -X POST "http://localhost:8083/api/v1/inventory/reserve" \
     -H "Content-Type: application/json" \
     -d '{
       "product_id": "550e8400-e29b-41d4-a716-446655440000",
       "location_id": "660e8400-e29b-41d4-a716-446655440000",
       "quantity": 5,
       "order_id": "770e8400-e29b-41d4-a716-446655440000",
       "expires_minutes": 60
     }'
```

### Adjusting Inventory

```bash
curl -X POST "http://localhost:8083/api/v1/inventory/adjust" \
     -H "Content-Type: application/json" \
     -d '{
       "product_id": "550e8400-e29b-41d4-a716-446655440000",
       "location_id": "660e8400-e29b-41d4-a716-446655440000",
       "quantity_change": 50,
       "adjustment_type": "restock",
       "reason": "New shipment received",
       "created_by": "warehouse_manager"
     }'
```

### Getting Low Stock Items

```bash
curl "http://localhost:8083/api/v1/inventory/low-stock?limit=10"
```

## Monitoring

### Metrics

The service exposes Prometheus metrics at `/metrics`:

- HTTP request metrics (duration, count, status codes)
- Inventory operation metrics
- Database connection pool metrics
- Custom business metrics (reservations, low stock alerts)

### Health Checks

- `/health` - Basic health check
- `/health/ready` - Readiness probe (checks database connectivity)
- `/health/live` - Liveness probe (process health)

### Logging

Structured JSON logging with correlation IDs for request tracing:

```json
{
  "timestamp": "2025-01-29T12:00:00Z",
  "level": "info",
  "service": "inventory-management-service",
  "environment": "development",
  "message": "Inventory reserved successfully",
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity": 5,
  "order_id": "770e8400-e29b-41d4-a716-446655440000"
}
```

## Testing

The service includes comprehensive tests with >60% coverage:

### Test Categories
- **Unit Tests**: Core business logic and repository operations
- **Integration Tests**: API endpoints with database
- **Health Check Tests**: All health and monitoring endpoints

### Running Tests

```bash
# All tests with coverage
make test-cov

# Specific test files
python -m pytest tests/test_inventory.py -v
python -m pytest tests/test_reservations.py -v
python -m pytest tests/test_locations.py -v

# With coverage report
python -m pytest --cov=src --cov-report=html
```

## Development

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Run all checks (format + lint + test)
make check
```

### Database Management

```bash
# Initialize database
make db-init

# Reset database (WARNING: destroys data)
make db-reset

# View current migrations
# (Alembic integration ready for production)
```

## Production Deployment

### Docker Production Build

```bash
docker build --target production -t inventory-management-service:latest .
```

### Environment Configuration

For production deployment, ensure:

1. **Database**: Use a managed PostgreSQL instance
2. **Environment Variables**: Set appropriate values for production
3. **Health Checks**: Configure Kubernetes probes to use `/health/ready` and `/health/live`
4. **Monitoring**: Configure Prometheus scraping and Grafana dashboards
5. **Security**: Add authentication middleware (planned for Phase 2)

### Kubernetes Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventory-management-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inventory-management-service
  template:
    metadata:
      labels:
        app: inventory-management-service
    spec:
      containers:
      - name: inventory-management-service
        image: inventory-management-service:latest
        ports:
        - containerPort: 8083
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: inventory-db-secret
              key: connection-string
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8083
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8083
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Contributing

1. Follow the established patterns from the existing codebase
2. Maintain test coverage above 60%
3. Use structured logging with appropriate context
4. Follow the repository pattern for data access
5. Add appropriate error handling and validation
6. Update documentation for new features

## License

MIT License - see LICENSE file for details.