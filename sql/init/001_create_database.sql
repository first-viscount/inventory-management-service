-- Initialize the inventory management database

-- Create database if it doesn't exist (this is handled by Docker environment)
-- The database is created by the postgres Docker image initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create enum types
DO $$ BEGIN
    CREATE TYPE location_type AS ENUM ('warehouse', 'store', 'online', 'dropship');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE reservation_status AS ENUM ('active', 'expired', 'released', 'completed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE adjustment_type AS ENUM ('restock', 'damage', 'theft', 'correction', 'return', 'manual');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions to the inventory user
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;
GRANT ALL ON SCHEMA public TO inventory_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO inventory_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO inventory_user;

-- Create a simple health check function
CREATE OR REPLACE FUNCTION health_check()
RETURNS TEXT
LANGUAGE SQL
AS $$
    SELECT 'OK'::TEXT;
$$;